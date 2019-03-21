import datetime
import itertools
import os
import subprocess
import sys
import tempfile

import pytest

from airflow.exceptions import AirflowException
from airflow.models import TaskInstance

from dagster_airflow.scaffold import (
    coalesce_execution_steps,
    _key_for_marshalled_result,
    _normalize_key,
)

from .utils import import_module_from_path

if sys.platform == 'darwin':
    TEMP_DIR = '/tmp'
else:
    TEMP_DIR = tempfile.gettempdir()


def test_unit_run_airflow_dag_steps(scaffold_dag):
    '''This test runs the steps in the sample Airflow DAG using the ``airflow test`` API.'''

    pipeline_name, execution_plan, execution_date, _s, _e = scaffold_dag

    for (solid_name, solid_steps) in coalesce_execution_steps(execution_plan):
        task_id = solid_name

        step_output_keys = set([])
        for step in solid_steps:
            for step_output in step.step_outputs:
                step_output_keys.add((step.key, step_output.name))

        for solid_step in solid_steps:
            for step_input in solid_step.step_inputs:
                step_input_key = (
                    step_input.prev_output_handle.step_key,
                    step_input.prev_output_handle.output_name,
                )
                if step_input_key in step_output_keys:
                    continue

                assert os.path.isfile(
                    _key_for_marshalled_result(
                        step_input.prev_output_handle.step_key,
                        step_input.prev_output_handle.output_name,
                        prepend_run_id=False,
                    ).format(tmp=os.path.join(TEMP_DIR, 'results', ''), sep='')
                )

        try:
            res = subprocess.check_output(
                ['airflow', 'test', pipeline_name, task_id, execution_date]
            )
        except subprocess.CalledProcessError as cpe:
            raise Exception('Process failed with output {}'.format(cpe.output))

        assert 'EXECUTION_PLAN_STEP_SUCCESS' in str(res)

        for solid_step in solid_steps:
            for step_output in solid_step.step_outputs:
                assert 'for output {output_name}'.format(output_name=step_output.name) in str(res)

                assert os.path.isfile(
                    _key_for_marshalled_result(
                        solid_step.key, step_output.name, prepend_run_id=False
                    ).format(tmp=os.path.join(TEMP_DIR, 'results', ''), sep='')
                )


def test_run_airflow_dag(scaffold_dag):
    '''This test runs the sample Airflow dag using the TaskInstance API, directly from Python'''
    _n, _p, _d, static_path, editable_path = scaffold_dag

    execution_date = datetime.datetime.utcnow()

    import_module_from_path('demo_pipeline_static__scaffold', static_path)
    demo_pipeline = import_module_from_path('demo_pipeline', editable_path)

    _dag, tasks = demo_pipeline.make_dag(
        dag_id=demo_pipeline.DAG_ID,
        dag_description=demo_pipeline.DAG_DESCRIPTION,
        dag_kwargs=dict(default_args=demo_pipeline.DEFAULT_ARGS, **demo_pipeline.DAG_KWARGS),
        s3_conn_id=demo_pipeline.S3_CONN_ID,
        operator_kwargs=demo_pipeline.OPERATOR_KWARGS,
        host_tmp_dir=demo_pipeline.HOST_TMP_DIR,
    )

    # These are in topo order already
    for task in tasks:
        ti = TaskInstance(task=task, execution_date=execution_date)
        context = ti.get_template_context()
        task.execute(context)


def test_run_airflow_error_dag(scaffold_error_dag):
    '''This test runs the sample Airflow dag using the TaskInstance API, directly from Python'''
    _n, _p, _d, static_path, editable_path = scaffold_error_dag

    execution_date = datetime.datetime.utcnow()

    import_module_from_path('demo_error_pipeline_static__scaffold', static_path)
    demo_pipeline = import_module_from_path('demo_error_pipeline', editable_path)

    _dag, tasks = demo_pipeline.make_dag(
        dag_id=demo_pipeline.DAG_ID,
        dag_description=demo_pipeline.DAG_DESCRIPTION,
        dag_kwargs=dict(default_args=demo_pipeline.DEFAULT_ARGS, **demo_pipeline.DAG_KWARGS),
        s3_conn_id=demo_pipeline.S3_CONN_ID,
        operator_kwargs=demo_pipeline.OPERATOR_KWARGS,
        host_tmp_dir=demo_pipeline.HOST_TMP_DIR,
    )

    # These are in topo order already
    for task in tasks:
        ti = TaskInstance(task=task, execution_date=execution_date)
        context = ti.get_template_context()
        with pytest.raises(AirflowException, match='Unusual error'):
            task.execute(context)