import unicodedata
import zlib
from pathlib import Path

from pikepdf import Dictionary, Name, Pdf
from pikepdf.canvas import Font


class GlyphlessFont(Font):
    """
    Font without glyphs. Shamelessly copied from https://github.com/ocrmypdf/OCRmyPDF.
    """
    # ------------------------------------------------------------------------------------------------------------------
    CID_TO_GID_DATA = zlib.compress(b"\x00\x01" * 65536)
    GLYPHLESS_FONT = (Path(__file__).resolve().parent.parent / 'data/pdf.ttf').read_bytes()
    CHAR_ASPECT = 2

    # ------------------------------------------------------------------------------------------------------------------
    def text_width(self, text: str, fontsize: float) -> float:
        """
        Estimates the width of a text string when rendered with the given font.
        """
        # NFKC: split ligatures, combine diacritics
        return len(unicodedata.normalize("NFKC", text)) * (fontsize / self.CHAR_ASPECT)

    # ------------------------------------------------------------------------------------------------------------------
    def text_encode(self, text: str) -> bytes:
        """
        Encodes the text using the codec registered for encoding.

        :param text: The text.
        """
        return text.encode('utf-16be')

    # ------------------------------------------------------------------------------------------------------------------
    def register(self, pdf: Pdf):
        """
        Registers the glyphless font.

        Create several data structures in the PDF to describe the font. While it creates
        the data, a reference should be set in at least one page's /Resources dictionary
        to retain the font in the output PDF and ensure it is usable on that page.
        """
        PLACEHOLDER = Name.Placeholder

        basefont = pdf.make_indirect(Dictionary(BaseFont=Name.GlyphLessFont,
                                                DescendantFonts=[PLACEHOLDER],
                                                Encoding=Name("/Identity-H"),
                                                Subtype=Name.Type0,
                                                ToUnicode=PLACEHOLDER,
                                                Type=Name.Font)
                                     )
        cid_font_type2 = pdf.make_indirect(Dictionary(BaseFont=Name.GlyphLessFont,
                                                      CIDToGIDMap=PLACEHOLDER,
                                                      CIDSystemInfo=Dictionary(Ordering="Identity",
                                                                               Registry="Adobe",
                                                                               Supplement=0),
                                                      FontDescriptor=PLACEHOLDER,
                                                      Subtype=Name.CIDFontType2,
                                                      Type=Name.Font,
                                                      DW=1000 // self.CHAR_ASPECT))

        basefont.DescendantFonts = [cid_font_type2]
        cid_font_type2.CIDToGIDMap = pdf.make_stream(self.CID_TO_GID_DATA, Filter=Name.FlateDecode)
        basefont.ToUnicode = pdf.make_stream(b"/CIDInit /ProcSet findresource begin\n"
                                             b"12 dict begin\n"
                                             b"begincmap\n"
                                             b"/CIDSystemInfo\n"
                                             b"<<\n"
                                             b"  /Registry (Adobe)\n"
                                             b"  /Ordering (UCS)\n"
                                             b"  /Supplement 0\n"
                                             b">> def\n"
                                             b"/CMapName /Adobe-Identify-UCS def\n"
                                             b"/CMapType 2 def\n"
                                             b"1 begincodespacerange\n"
                                             b"<0000> <FFFF>\n"
                                             b"endcodespacerange\n"
                                             b"1 beginbfrange\n"
                                             b"<0000> <FFFF> <0000>\n"
                                             b"endbfrange\n"
                                             b"endcmap\n"
                                             b"CMapName currentdict /CMap defineresource pop\n"
                                             b"end\n"
                                             b"end\n")
        font_descriptor = pdf.make_indirect(Dictionary(Ascent=1000,
                                                       CapHeight=1000,
                                                       Descent=-1,
                                                       Flags=5,  # Fixed pitch and symbolic
                                                       FontBBox=[0, 0, 1000 // self.CHAR_ASPECT, 1000],
                                                       FontFile2=PLACEHOLDER,
                                                       FontName=Name.GlyphLessFont,
                                                       ItalicAngle=0,
                                                       StemV=80,
                                                       Type=Name.FontDescriptor))
        font_descriptor.FontFile2 = pdf.make_stream(self.GLYPHLESS_FONT)
        cid_font_type2.FontDescriptor = font_descriptor

        return basefont

# ----------------------------------------------------------------------------------------------------------------------
