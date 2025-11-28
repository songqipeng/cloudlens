from core.analyzer_registry import AnalyzerRegistry
from core.base_analyzer import BaseResourceAnalyzer


def test_register_analyzer():
    @AnalyzerRegistry.register("test", "Test Analyzer", "🧪")
    class DummyAnalyzer(BaseResourceAnalyzer):
        def get_resource_type(self):
            return "test"

        def get_all_regions(self):
            return []

        def get_instances(self, region):
            return []

        def get_metrics(self, region, instance_id, days=14):
            return {}

        def is_idle(self, instance, metrics, thresholds=None):
            return False, []

        def get_optimization_suggestions(self, instance, metrics):
            return ""

    info = AnalyzerRegistry.get_analyzer_info("test")
    assert info is not None
    assert info["display_name"] == "Test Analyzer"
    assert info["emoji"] == "🧪"
