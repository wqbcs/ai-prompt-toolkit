"""R62: 供应链安全检测器AI工具链扩展测试"""

from __future__ import annotations


class TestSupplyChainAIToolchain:
    def test_pickle_load_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("model = pickle.load(open('model.pkl', 'rb'))")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0
        assert ai_matches[0].risk_level == "critical"

    def test_torch_load_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("checkpoint = torch.load('model.pt')")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0

    def test_mlflow_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("mlflow run experiment --tracking-uri http://server")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0
        assert ai_matches[0].risk_level == "high"

    def test_huggingface_model_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("model = AutoModel.from_pretrained('org/unknown-model')")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0

    def test_docker_command_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("docker run --rm -p 5000:5000 ml-model:latest")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0
        assert ai_matches[0].risk_level == "high"

    def test_no_toolchain_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("你是一个智能助手，请回答以下问题。")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) == 0

    def test_check_includes_toolchain(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        finding = det.check("使用pickle.load加载模型和docker run部署服务")
        assert finding is not None
        assert finding.rule_id == "SC001"

    def test_ray_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("ray init --address=ray://cluster:10001")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0

    def test_hub_load_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("model = torch.hub.load('repo', 'model')")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0
        assert ai_matches[0].risk_level == "medium"

    def test_framework_dependency_risk(self):
        from ai_prompt_toolkit.security.supply_chain_detector import SupplyChainDetector

        det = SupplyChainDetector()
        matches = det.detect("使用transformers.pipeline进行推理")
        ai_matches = [m for m in matches if m.match_type == "ai_ml_toolchain"]
        assert len(ai_matches) > 0
        assert ai_matches[0].risk_level == "low"
