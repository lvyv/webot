import logging

_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        root_logger = logging.getLogger()
        old_level = root_logger.level

        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(use_doc_unwarping=False)

        root_logger.setLevel(old_level)

        for name in ('ppocr', 'paddle', 'paddleocr'):
            logging.getLogger(name).setLevel(logging.WARNING)
    return _ocr_engine
