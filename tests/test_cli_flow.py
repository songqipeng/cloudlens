import pytest
from unittest.mock import MagicMock, patch
from cloudlens.click.testing import CliRunner
from cloudlens.cli.main from cloudlens import cli
from cloudlens.cli.utils import get_provider
from cloudlens.core.config import CloudAccount
from cloudlens.models.resource import UnifiedResource, ResourceType, ResourceStatus
from datetime import datetime, timedelta

# Mock Resources
def create_mock_resource(id, name, type, status, region="cn-hangzhou"):
    r = UnifiedResource(
        id=id,
        name=name,
        provider="aliyun",
        region=region,
        resource_type=type,
        status=status
    )
    r.public_ips = ["1.2.3.4"]
    r.private_ips = ["192.168.1.1"]
    r.expired_time = datetime.now() + timedelta(days=60)
    return r

@pytest.fixture
def mock_config_manager():
    with patch("core.config.ConfigManager") as MockCM:
        cm = MockCM.return_value
        
        # Mock accounts
        acc1 = CloudAccount(name="prod", provider="aliyun", region="cn-hangzhou", access_key_id="ak1")
        acc2 = CloudAccount(name="test", provider="tencent", region="ap-guangzhou", access_key_id="ak2")
        
        cm.list_accounts.return_value = [acc1, acc2]
        cm.get_account.side_effect = lambda name, p=None: acc1 if name == "prod" else (acc2 if name == "test" else None)
        
        yield cm

@pytest.fixture
def mock_provider():
    with patch("cli.utils.get_provider") as mock_get_prov:
        provider = MagicMock()
        provider.provider_name = "aliyun"
        mock_get_prov.return_value = provider
        
        # Mock ECS
        provider.list_instances.return_value = [
            create_mock_resource("i-1", "web-server", ResourceType.ECS, ResourceStatus.RUNNING),
            create_mock_resource("i-2", "db-server", ResourceType.ECS, ResourceStatus.STOPPED)
        ]
        
        # Mock RDS
        provider.list_rds.return_value = [
            create_mock_resource("rm-1", "mysql-prod", ResourceType.RDS, ResourceStatus.RUNNING)
        ]
        
        # Mock Redis
        provider.list_redis.return_value = [
            create_mock_resource("r-1", "redis-cache", ResourceType.REDIS, ResourceStatus.RUNNING)
        ]
        
        # Mock OSS
        provider.list_oss.return_value = [
            {"name": "bucket-1", "region": "cn-hangzhou", "storage_class": "Standard", "created_time": "2023-01-01"}
        ]
        
        # Mock VPC
        provider.list_vpcs.return_value = [
            {"id": "vpc-1", "name": "main-vpc", "cidr": "10.0.0.0/16", "region": "cn-hangzhou", "status": "Available"}
        ]
        
        # Mock EIP
        provider.list_eip.return_value = [
            {"id": "eip-1", "ip_address": "1.2.3.4", "status": "InUse", "instance_id": "i-1", "region": "cn-hangzhou"}
        ]
        
        # Mock SLB
        provider.list_slb.return_value = [
            {"id": "lb-1", "name": "web-lb", "address": "1.2.3.5", "address_type": "internet", "status": "active", "region": "cn-hangzhou"}
        ]
        
        # Mock NAS
        provider.list_nas.return_value = [
            {"id": "nas-1", "protocol_type": "NFS", "storage_type": "Performance", "status": "Running", "metered_size": 107374182400, "region": "cn-hangzhou"}
        ]
        
        yield provider

def test_config_list(mock_config_manager):
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "aliyun" in result.output

def test_query_ecs(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "ecs", "--account", "prod"])
    assert result.exit_code == 0
    assert "i-1" in result.output
    assert "web-server" in result.output
    assert "Running" in result.output

def test_query_rds(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "rds", "--account", "prod"])
    assert result.exit_code == 0
    assert "rm-1" in result.output
    assert "mysql-prod" in result.output

def test_query_redis(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "redis", "--account", "prod"])
    assert result.exit_code == 0
    assert "r-1" in result.output

def test_query_oss(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "oss", "--account", "prod"])
    assert result.exit_code == 0
    assert "bucket-1" in result.output

def test_query_vpc(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "vpc", "--account", "prod"])
    assert result.exit_code == 0
    assert "vpc-1" in result.output

def test_query_eip(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "eip", "--account", "prod"])
    assert result.exit_code == 0
    assert "eip-1" in result.output

def test_query_slb(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "slb", "--account", "prod"])
    assert result.exit_code == 0
    assert "lb-1" in result.output

def test_query_nas(mock_config_manager, mock_provider):
    runner = CliRunner()
    result = runner.invoke(cli, ["query", "nas", "--account", "prod"])
    assert result.exit_code == 0
    assert "nas-1" in result.output
    assert "100.00" in result.output # 100GB

def test_analyze_renewal(mock_config_manager, mock_provider):
    runner = CliRunner()
    # Mock expired time to be soon
    mock_provider.list_instances.return_value[0].expired_time = datetime.now() + timedelta(days=5)
    
    result = runner.invoke(cli, ["analyze", "renewal", "--days", "7", "--account", "prod"])
    assert result.exit_code == 0
    assert "i-1" in result.output
    assert "5" in result.output # days left

def test_analyze_tags(mock_config_manager, mock_provider):
    with patch("core.tag_analyzer.TagAnalyzer.analyze_tag_coverage") as mock_analyze:
        mock_analyze.return_value = {
            "total": 10, "tagged": 8, "untagged": 2, "coverage_rate": 80.0,
            "untagged_resources": [create_mock_resource("i-3", "no-tag", ResourceType.ECS, ResourceStatus.RUNNING)]
        }
        with patch("core.tag_analyzer.TagAnalyzer.analyze_tag_keys") as mock_keys:
            mock_keys.return_value = {"most_common": [("Project", 5)]}
            with patch("core.tag_analyzer.TagAnalyzer.suggest_tag_optimization") as mock_sugg:
                mock_sugg.return_value = ["Add Project tag"]
                
                runner = CliRunner()
                result = runner.invoke(cli, ["analyze", "tags", "--account", "prod"])
                assert result.exit_code == 0
                assert "80.0%" in result.output
                assert "i-3" in result.output

def test_analyze_security(mock_config_manager, mock_provider):
    with patch("core.security_compliance.SecurityComplianceAnalyzer.detect_public_exposure") as mock_detect:
        mock_detect.return_value = [{"id": "i-1", "name": "web", "type": "ECS", "public_ips": ["1.2.3.4"], "risk_level": "High"}]
        with patch("core.security_compliance.SecurityComplianceAnalyzer.analyze_eip_usage") as mock_eip:
            mock_eip.return_value = {"total": 5, "bound": 4, "unbound": 1, "unbound_rate": 20.0, "unbound_eips": [{"id": "eip-x", "ip_address": "5.6.7.8"}]}
            with patch("core.security_compliance.SecurityComplianceAnalyzer.suggest_security_improvements") as mock_sugg:
                mock_sugg.return_value = ["Fix exposure"]
                
                runner = CliRunner()
                result = runner.invoke(cli, ["analyze", "security", "--account", "prod"])
                assert result.exit_code == 0
                assert "i-1" in result.output
                assert "eip-x" in result.output

def test_analyze_idle(mock_config_manager, mock_provider):
    with patch("core.idle_detector.IdleDetector.fetch_ecs_metrics") as mock_metrics:
        mock_metrics.return_value = {"cpu_avg": 1.0, "mem_avg": 10.0} # Low usage
        with patch("core.idle_detector.IdleDetector.is_ecs_idle") as mock_is_idle:
            mock_is_idle.return_value = (True, ["Low CPU usage"])
            
            runner = CliRunner()
            result = runner.invoke(cli, ["analyze", "idle", "--account", "prod"])
            assert result.exit_code == 0
            assert "i-1" in result.output
            assert "Low CPU usage" in result.output

def test_report_generate_excel(mock_config_manager, mock_provider):
    with patch("core.report_generator.ReportGenerator.generate_excel") as mock_gen:
        runner = CliRunner()
        result = runner.invoke(cli, ["report", "generate", "--account", "prod", "--format", "excel", "--output", "report.xlsx"])
        assert result.exit_code == 0
        assert "Excel report saved" in result.output
        mock_gen.assert_called_once()

def test_report_generate_html(mock_config_manager, mock_provider):
    with patch("core.report_generator.ReportGenerator.generate_html") as mock_gen:
        mock_gen.return_value = "<html></html>"
        with patch("core.report_generator.ReportGenerator.save_html") as mock_save:
            runner = CliRunner()
            result = runner.invoke(cli, ["report", "generate", "--account", "prod", "--format", "html", "--output", "report.html"])
            assert result.exit_code == 0
            assert "HTML report saved" in result.output
            mock_gen.assert_called_once()
            mock_save.assert_called_once()

def test_topology_generate(mock_config_manager, mock_provider):
    with patch("core.topology_generator.TopologyGenerator.generate_markdown_report") as mock_gen:
        mock_gen.return_value = "# Topology"
        # Mock open to avoid writing file
        with patch("builtins.open", new_callable=MagicMock):
            runner = CliRunner()
            result = runner.invoke(cli, ["topology", "generate", "--account", "prod", "--output", "topo.md"])
            assert result.exit_code == 0
            assert "Topology saved" in result.output
            mock_gen.assert_called_once()

def test_analyze_cost(mock_config_manager, mock_provider):
    with patch("core.cost_analyzer.CostAnalyzer.analyze_renewal_costs") as mock_renewal:
        mock_renewal.return_value = {
            "total_prepaid": 5,
            "expiring_soon": [{"id": "i-1", "name": "web", "spec": "2c4g", "expire_date": "2023-12-31", "days_left": 5}]
        }
        with patch("core.cost_analyzer.CostAnalyzer.suggest_discount_optimization") as mock_sugg:
            mock_sugg.return_value = []
            with patch("core.cost_analyzer.CostAnalyzer.calculate_monthly_estimate") as mock_est:
                mock_est.return_value = {"total_monthly_estimate": 100.0, "note": "Est"}
                
                runner = CliRunner()
                result = runner.invoke(cli, ["analyze", "cost", "--account", "prod"])
                assert result.exit_code == 0
                assert "续费成本分析" in result.output
                assert "i-1" in result.output
                assert "100.00" in result.output

def test_query_tencent_cvm(mock_config_manager):
    # Need to mock get_provider to return a provider with provider_name='tencent'
    with patch("cli.utils.get_provider") as mock_get_prov:
        provider = MagicMock()
        provider.provider_name = "tencent"
        provider.list_instances.return_value = [
            create_mock_resource("ins-1", "tencent-vm", ResourceType.ECS, ResourceStatus.RUNNING, region="ap-guangzhou")
        ]
        mock_get_prov.return_value = provider
        
        runner = CliRunner()
        result = runner.invoke(cli, ["query", "ecs", "--account", "test"])
        assert result.exit_code == 0
        assert "ins-1" in result.output
        assert "tencent-vm" in result.output



