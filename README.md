# webot
WeChat robot framework based on cv.

1.Use it as a common agent of an organization, intercommunication between customers and employees.  
2.LLM Wiki methodology by Dr. Karpathy instead of the traditional RAG.  
3.Friendly for modifications.  

## 1.Quick Start
### step 1 Setting up Pycharm IDE.  
![img.png](docs/images/img.png)
### step 2 Some import python packages.  
```commandline
uv add torch torchvision torchaudio
uv pip install paddlepaddle-gpu==3.0.0 --default-index https://www.paddlepaddle.org.cn/packages/stable/cu118/  
uv pip install "paddleocr[all]"
```
### step 3 Give a try.
```python
import paddle
print("CUDA available:", paddle.is_compiled_with_cuda())
```

## 2.Design Consideration
### 2.1AgentLoop的ticker
（1）UI层的Timer会5秒一次触发，在窗口的事件处理函数中，主要功能是调用AgentLoop的ticker函数，根据结果绘制到界面上。  
（2）UI窗口创建的时候会附带AgentLoop的实例agent被创建。UI起来之后，点击“开始监控”按钮，定时器启动，“停止监控”，定时器关闭。  
（3）AgentLoop的ticker函数完成核心功能是每个ticker周期观察一次界面（发现红点），产生任务。按照目前的机制，Agent起来之前的红点不处理，只记录到_seen_chats中，只有是Agent运行起来之后，新到来的消息，Agent才会根据rules.json中设置的哪些联系人以及群需要自动回复，以及回复的规则去处理。
【注意】这个设计是比较合理的，就是尽量让新消息由人去处理而不是Agent已启动，就把所有消息都自动处理掉。  
（4）Agent目前处理消息是每次处理一个联系人，在_handle_one中处理。这个函数内部再按照模板处理或者大模型处理。
