from paddleocr import PaddleOCR

ocr = PaddleOCR()
result = ocr.predict(input='./images/blackboard.jpg')

for res in result:
    # 1. 打印结构化信息到控制台
    res.print()

    # 2. 保存可视化结果到图片（会自动创建 'output' 目录）
    res.save_to_img("output")

    # 3. 保存为 JSON 文件，便于程序化处理
    res.save_to_json("output")