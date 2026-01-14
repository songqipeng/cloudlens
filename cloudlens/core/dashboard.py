from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Label, Static, Tree
from textual.widgets.tree import TreeNode

from cloudlens.core.analyzer_registry import AnalyzerRegistry
from cloudlens.core.config import ConfigManager


class ResourceTree(Tree):
    """资源导航树"""

    pass


class CloudLensApp(App):
    """CloudLens TUI Dashboard"""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 3fr;
    }

    ResourceTree {
        dock: left;
        width: 30%;
        height: 100%;
        border: solid green;
    }

    DataTable {
        width: 100%;
        height: 100%;
        border: solid blue;
    }
    
    .box {
        height: 100%;
        border: solid green;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Horizontal(
            ResourceTree("Cloud Resources", id="tree"),
            DataTable(id="table"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Event handler called when widget is added to the app."""
        self.title = "CloudLens Dashboard"
        self.sub_title = "Multi-Cloud Resource Monitor"

        # 初始化资源树
        tree = self.query_one(ResourceTree)
        tree.root.expand()

        # 加载资源类型
        analyzers = AnalyzerRegistry.list_analyzers()

        # 按类别分组 (模拟)
        categories = {
            "Compute": ["ecs", "ack", "eci"],
            "Database": ["rds", "redis", "mongodb", "polardb", "clickhouse"],
            "Network": ["vpc", "slb", "eip", "nat", "vpn"],
            "Storage": ["oss", "nas", "disk"],
            "Others": [],
        }

        for category, types in categories.items():
            cat_node = tree.root.add(category, expand=True)
            for r_type in types:
                if r_type in analyzers:
                    info = analyzers[r_type]
                    label = Text(f"{info['emoji']} {info['display_name']}")
                    cat_node.add(label, data=r_type)

        # 初始化表格
        table = self.query_one(DataTable)
        table.add_columns("ID", "Name", "Region", "Status")

    def on_tree_node_selected(self, message: Tree.NodeSelected) -> None:
        """Event handler called when a tree node is selected."""
        if not message.node.data:
            return

        resource_type = message.node.data
        self.load_resources(resource_type)

    def load_resources(self, resource_type: str):
        """加载资源数据到表格"""
        table = self.query_one(DataTable)
        table.clear()

        # 这里为了演示，我们只加载配置的账号信息，实际应该调用 Analyzer
        # 由于 TUI 中进行网络请求会阻塞 UI，理想情况应该用 Worker
        # 这里简化处理，只显示"Loading..."

        cm = ConfigManager()
        accounts = cm.list_accounts()

        # 模拟数据加载 (实际应调用 API)
        # table.add_row("Loading...", "Please wait", "...", "...")

        # 尝试获取 Analyzer 类
        analyzer_cls = AnalyzerRegistry.get_analyzer_class(resource_type)
        if not analyzer_cls:
            return

        # 简单的同步加载 (可能会卡顿，仅作演示)
        count = 0
        for acc in accounts:
            if acc.provider != "aliyun":
                continue
            try:
                # 仅演示，不真实调用 API 以免卡顿太久，或者只调用一个区域
                # analyzer = analyzer_cls(acc.access_key_id, acc.access_key_secret, acc.name)
                # instances = analyzer.get_instances("cn-hangzhou")
                # for inst in instances:
                #     table.add_row(inst.get('InstanceId'), inst.get('InstanceName'), "cn-hangzhou", inst.get('Status'))

                # Mock 数据用于展示 TUI 效果
                table.add_row(
                    f"i-{resource_type}-001",
                    f"{acc.name}-{resource_type}-1",
                    "cn-hangzhou",
                    "Running",
                )
                table.add_row(
                    f"i-{resource_type}-002",
                    f"{acc.name}-{resource_type}-2",
                    "cn-beijing",
                    "Stopped",
                )
                count += 2
            except Exception:
                pass

        if count == 0:
            table.add_row("No resources found", "", "", "")


if __name__ == "__main__":
    app = CloudLensApp()
    app.run()
