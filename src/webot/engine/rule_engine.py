import importlib.util
import os
import sys

from .nodes.base import RuleNode
from ..utils import get_logger

logger = get_logger(__name__)


def _load_node_module(filepath: str) -> RuleNode | None:
    """动态加载 .py 节点文件，返回 RuleNode 实例。"""
    if not os.path.isfile(filepath):
        logger.error(f"节点文件不存在: {filepath}")
        return None

    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        logger.error(f"加载节点模块失败 {filepath}: {e}")
        return None

    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, type) and issubclass(attr, RuleNode) and attr is not RuleNode:
            return attr()
    logger.error(f"节点文件中未找到 RuleNode 子类: {filepath}")
    return None


class RuleEngine:
    """规则引擎：加载 flow JSON，按 DAG 拓扑执行节点。"""

    def __init__(self, flow_path: str | None = None):
        self.flow_path = flow_path
        self.nodes: dict[str, RuleNode] = {}
        self.start_node: str = ""
        self._edges: list[dict] = []

    def load(self, flow_path: str) -> bool:
        import json
        try:
            with open(flow_path, "r", encoding="utf-8") as f:
                flow = json.load(f)
        except Exception as e:
            logger.error(f"读取 flow 文件失败 {flow_path}: {e}")
            return False

        self.flow_path = flow_path
        self.start_node = flow.get("start", "")
        self._edges = flow.get("edges", [])

        base_dir = os.path.dirname(os.path.abspath(flow_path))
        self.nodes.clear()
        for node_def in flow.get("nodes", []):
            node_id = node_def["id"]
            module_path = node_def.get("module", "")
            if not os.path.isabs(module_path):
                module_path = os.path.join(base_dir, module_path)
            node = _load_node_module(module_path)
            if node is None:
                logger.warning(f"节点 [{node_id}] 加载失败，跳过")
                continue
            node.name = node_id
            self.nodes[node_id] = node

        if self.start_node not in self.nodes:
            logger.error(f"起始节点 [{self.start_node}] 不在已加载节点中")
            return False

        logger.info(f"规则引擎已加载: {len(self.nodes)} 节点, start={self.start_node}")
        return True

    def execute(self, ctx: dict) -> dict:
        """执行规则流，返回最终输出。"""
        if self.start_node not in self.nodes:
            logger.error("规则引擎未加载或起始节点不存在")
            return {}

        current_id = self.start_node
        output = {}

        while current_id and current_id in self.nodes:
            node = self.nodes[current_id]
            logger.debug(f"规则引擎: 执行节点 [{current_id}]")
            try:
                result = node.execute(ctx)
            except Exception as e:
                logger.error(f"节点 [{current_id}] 执行异常: {e}")
                break

            if not isinstance(result, dict):
                break

            output = result
            ctx.update(result)
            current_id = result.get("next", None)

        return output
