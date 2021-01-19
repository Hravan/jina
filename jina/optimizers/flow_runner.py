import os
import shutil
from collections.abc import Iterable
from typing import Iterator, Optional

from ..flow import Flow
from ..helper import colored
from ..logging import default_logger as logger
from ..jaml import JAMLCompatibleSimple


class FlowRunner(JAMLCompatibleSimple):
    def run(
            self,
            trial_parameters: dict,
            workspace: str = 'workspace',
            **kwargs,
    ):
        """
        :param trial_parameters: parameters to be used as environment variables
        :param workspace: directory to be used for the flows
        """
        raise NotImplementedError

    def get_evaluations(self):
        raise NotImplementedError


class SingleFlowRunner(FlowRunner):
    """Module to define and run a flow."""

    def __init__(
            self,
            flow_yaml: str,
            documents: Iterator,
            request_size: int,
            task: str,  # this can be only index or search as it is used to call the flow API
            callback: Optional = None,
            overwrite_workspace: bool = False,
    ):
        """
        :param flow_yaml: path to flow yaml
        :param documents: iterator with list or generator for getting the documents
        :param request_size: request size used in the flow
        :param task: task of the flow which can be `index` or `search`
        :param callback: callback to be passed to the flow's `on_done`
        :param overwrite_workspace: overwrite workspace created by the flow
        """
        super().__init__()
        self.flow_yaml = flow_yaml
        # TODO: Make changes for working with doc generator (Pratik, before v1.0)

        if type(documents) is list:
            self.documents = documents
        elif type(documents) is str:
            self.documents = documents
        elif isinstance(documents, Iterable):
            self.documents = list(documents)
        else:
            raise TypeError(f"documents is of wrong type: {type(documents)}")

        self.request_size = request_size
        if task in ('index', 'search'):
            self.task = task
        else:
            raise ValueError('task can be either of index or search')
        self.callback = callback
        self.overwrite_workspace = overwrite_workspace

    def _setup_workspace(self, workspace):
        if os.path.exists(workspace):
            if self.overwrite_workspace:
                shutil.rmtree(workspace)
                logger.warning(colored('Existing workspace deleted', 'red'))
                logger.warning(colored('WORKSPACE: ' + str(workspace), 'red'))
                logger.warning(
                    colored('change overwrite_workspace to change this', 'red')
                )
            else:
                logger.warning(
                    colored(
                        f'Workspace {workspace} already exists. Please set ``overwrite_workspace=True`` for replacing it.',
                        'red',
                    )
                )

        os.makedirs(workspace, exist_ok=True)

    def run(
            self,
            trial_parameters: dict,
            workspace: str = 'workspace',
            **kwargs,
    ):
        """[summary]

        :param trial_parameters: flow env variable values
        :param workspace: directory to be used for artifacts generated
        """

        self._setup_workspace(workspace)
        self._reset_callback()

        with Flow.load_config(self.flow_yaml, context=trial_parameters) as f:
            getattr(f, self.task)(
                self.documents,
                request_size=self.request_size,
                on_done=self.callback,
                **kwargs,
            )

    def _reset_callback(self):
        self.callback = self.callback.get_fresh_callback()

    def get_evaluations(self):
        return self.callback.get_mean_evaluation()


class MultiFlowRunner(FlowRunner):
    """Chain and run multiple flows"""

    def __init__(self, *flows, eval_flow_index=-1):
        """
        :param flows: flows to be executed in sequence
        :param eval_flow_index: index of the evaluation flow in the sequence of flows in `MultiFlowRunner`

        """
        super().__init__()
        self.flows = flows
        self.eval_flow_index = eval_flow_index

    def run(
            self,
            trial_parameters: dict,
            workspace: str = 'workspace',
            **kwargs,
    ):
        """
        :param trial_parameters: parameters to be used as environment variables
        :param workspace: directory to be used for the flows
        """
        for flow in self.flows:
            flow.run(trial_parameters, workspace, **kwargs)

    def get_evaluations(self):
        return self.flows[self.eval_flow_index].get_evaluations()
