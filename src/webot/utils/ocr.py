import json
import logging
import os

_ocr_engine = None


class MockPage:
    """Simulates a single page result from PaddleOCR's OCRResult."""

    def __init__(self, data, stem):
        self._data = data
        self._stem = stem

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def save_to_img(self, output_dir):
        import cv2
        import numpy as np

        os.makedirs(output_dir, exist_ok=True)
        img = np.ones((400, 600, 3), dtype=np.uint8) * 255
        path = os.path.join(output_dir, f"{self._stem}_ocr_res_img.png")
        cv2.imwrite(path, img)

    def save_to_json(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{self._stem}_res.json")

        def _convert(v):
            import numpy as np
            if isinstance(v, np.ndarray):
                return v.tolist()
            if isinstance(v, np.generic):
                return v.item()
            return v

        data = {k: [_convert(x) for x in v] for k, v in self._data.items()}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


class MockPaddleOCR:
    """Mock PaddleOCR that returns fake results without loading models."""

    def __init__(self, **kwargs):
        self._texts = json.loads(
            os.environ.get(
                "WEBOT_MOCK_OCR_TEXTS",
                '["你好世界", "mock ocr 测试", "欢迎使用webot"]',
            )
        )

    def predict(self, input=None, **kwargs):
        import numpy as np

        stem = "mock_ocr_page"
        img_h, img_w = 800, 600

        if isinstance(input, str):
            stem = os.path.splitext(os.path.basename(input))[0]
        elif isinstance(input, np.ndarray):
            img_h, img_w = input.shape[:2]

        n = len(self._texts)
        rec_texts = self._texts
        rec_scores = [round(0.85 + i * 0.05, 2) for i in range(n)]

        line_h = max(24, img_h // (n * 3 + 1))
        box_w = img_w * 7 // 10
        margin = img_w // 10
        rec_boxes = [
            [margin, margin + i * line_h * 3, margin + box_w, margin + i * line_h * 3 + line_h]
            for i in range(n)
        ]
        rec_polys = [
            np.array([[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]], dtype=np.float32)
            for b in rec_boxes
        ]

        data = {
            "rec_texts": rec_texts,
            "rec_scores": rec_scores,
            "rec_boxes": rec_boxes,
            "rec_polys": rec_polys,
        }

        return [MockPage(data, stem)]


def _is_mock_mode():
    return os.environ.get("WEBOT_MOCK_OCR", "").lower() in ("1", "true", "yes")


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        if _is_mock_mode():
            _ocr_engine = MockPaddleOCR()
        else:
            root_logger = logging.getLogger()
            old_level = root_logger.level

            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_doc_unwarping=False)

            root_logger.setLevel(old_level)

            for name in ('ppocr', 'paddle', 'paddleocr'):
                logging.getLogger(name).setLevel(logging.WARNING)
    return _ocr_engine
