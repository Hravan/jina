import uuid
from tempfile import SpooledTemporaryFile

from jina.flow import Flow
from .base import BaseStore


class FlowStore(BaseStore):

    def add(self, config: SpooledTemporaryFile):
        try:
            y_spec = config.read().decode()
            f = Flow.load_config(y_spec).start()
            _id = uuid.UUID(f.args.identity)
        except Exception as e:
            self._logger.error(f'{e!r}')
            raise
        else:
            self[_id] = {
                'object': f,
                'arguments': vars(f.args),
                'yaml_source': y_spec
            }
            return _id
