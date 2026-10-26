"""Fixed G3 M1 service identity; decoding/cache remain the G5 implementation."""

from toolalign.model_io.cuda_evaluation import CUDAEvaluationBackend


class CUDAServiceBackend(CUDAEvaluationBackend):
    backend_label = "cuda-service.v1"
    lease_task_id = "P07-G6-SERVING"
    lease_job = "serving"

    def __init__(self, *, cache_enabled, **kwargs):
        super().__init__(model="M1", cache_enabled=cache_enabled,
                         tenant_id="not-dispatched", **kwargs)
        self._service_metrics = {}

    def bind_principal(self, principal):
        self._require_owned_child()
        self.tenant_id = principal

    def generation_metrics(self):
        return dict(self._service_metrics)

    def generate(self, request, generation_config):
        self._service_metrics = {}
        before = len(self._metrics.get("decisions", []))
        try:
            return super().generate(request, generation_config)
        finally:
            decisions = self._metrics.get("decisions", [])
            if len(decisions) > before:
                self._service_metrics = dict(decisions[-1])
