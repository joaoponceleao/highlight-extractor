import pathlib
import pdb
from glob import iglob

import fitz

PADDING = 7
DPI = 150


def make_text(words):
    """Return textstring output of get_text("words").
    Word items are sorted for reading sequence left to right,
    top to bottom.
    """
    line_dict = {}  # key: vertical coordinate, value: list of words
    words.sort(key=lambda w: w[0])  # sort by horizontal coordinate
    for w in words:  # fill the line dictionary
        y1 = round(w[3], 1)  # bottom of a word: don't be too picky!
        word = w[4]  # the text of the word
        line = line_dict.get(y1, [])  # read current line content
        line.append(word)  # append new word
        line_dict[y1] = line  # write back to dict
    lines = list(line_dict.items())
    lines.sort()  # sort vertically
    return "\n".join([" ".join(line[1]) for line in lines])


annotations = {}
for pdf in iglob("*.pdf"):
    with fitz.open(pdf) as doc:
        if doc.has_annots():
            pathlib.Path(f"annotations/{pdf}").mkdir(parents=True, exist_ok=True)
            annotations[pdf] = []
            for page in doc.pages():
                for annot in page.annots():
                    if 1 < annot.border["width"] < 2:
                        # Annotation is ink. Assume image clip or handwritten annotation.
                        # Extract annotation, in case it's handwritten, and background, in case it is a clip.
                        anot_img = page.get_pixmap(
                            clip=annot.rect.irect, dpi=DPI, annots=True
                        )
                        tl_x, tl_y, br_x, br_y = (
                            annot.rect.x0,
                            annot.rect.y0,
                            annot.rect.x1,
                            annot.rect.y1,
                        )
                        anot_img.save(
                            f"annotations/{pdf}/{page.number}/{tl_x}_{tl_y}_{br_x}_{br_y}.png"
                        )

                        annotations[pdf].append(
                            {
                                "page": page.number,
                                "topLeft": (tl_x, tl_y),
                                "bottomRight": (br_x, br_y),
                                "text": "",
                            }
                        )
                    else:
                        # Annotation is highlight (width of bet. 9-10).
                        # Extract text if ocr, otherwise extract background without annotation ink.
                        words = page.get_text("words")
                        highlight_words = [
                            w
                            for w in words
                            if fitz.Rect(w[:4]).intersects(annot.rect.irect)
                        ]
                        if highlight_words:
                            anot_text = make_text(highlight_words)
                        else:
                            tl_x, tl_y, br_x, br_y = (
                                annot.rect.x0,
                                annot.rect.y0,
                                annot.rect.x1,
                                annot.rect.y1,
                            )
                            anot_text = ""
                            anot_text_img = page.get_pixmap(
                                clip=annot.rect.irect, dpi=DPI, annots=False
                            )
                            anot_text_img.save(
                                f"annotations/{pdf}/{page.number}/{tl_x}_{tl_y}_{br_x}_{br_y}.png"
                            )
                        annotations[pdf].append(
                            {
                                "page": page.number,
                                "topLeft": (tl_x, tl_y),
                                "bottomRight": (br_x, br_y),
                                "text": anot_text,
                            }
                        )

if annotations:
    with open("annotations/index.html", "w") as annotation_index:
        annotation_index.write(
            "<!doctype html>\n<html>\n<head>Annotation Index</head><body>\n"
        )
        annotation_index.write("<ul>\n")
        for doc, annots in annotations.items():
            annotation_index.write(f"<li>{doc}</li>\n<ul>\n")
            current_page = -1
            for highlight in annots:
                if current_page < 0:
                    annotation_index.write(f"<li>p.{highlight['page']}</li><ul>")
                    current_page = highlight["page"]
                elif highlight["page"] != current_page:
                    annotation_index.write(
                        f"</ul>\n<li>p.{highlight['page']}</li>\n<ul>\n"
                    )
                    current_page = highlight["page"]
                annotation_index.write(f"<li><p>{highlight['text']}</p></li>")
                annotation_index.write(
                    f"<li><img src=\"{doc}/{highlight['page']}/{highlight['topLeft'][0]}_{highlight['topLeft'][1]}_{highlight['bottomRight'][0]}_{highlight['bottomRight'][1]}.png\"></li>\n"
                )
            annotation_index.write("</ul>\n")
            annotation_index.write("</ul>\n")
        annotation_index.write("</ul>\n")
        annotation_index.write("</body></html>")
