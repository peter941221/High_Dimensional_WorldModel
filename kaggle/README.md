# Kaggle Runner Files

- `run_kaggle_job.py`: Kaggle kernel entry script.
- `run_config.example.json`: configuration template for batch runs.
- `kernel-metadata.template.json`: metadata template reference.
- Runner executes experiment scripts directly (no Colab dependency).

Default flow uses a code dataset bundle:
- manager uploads `project_bundle.zip` to Kaggle Dataset
- kernel extracts it from `/kaggle/input/<code-dataset-slug>/project_bundle.zip`
- avoids runtime `git clone` dependency

The generated build bundle writes a runtime config to:

```text
kaggle/run_config.json
```

You normally do not edit this manually when using:

```bash
python kaggle_job_manager.py prepare ...
python kaggle_job_manager.py run ...
```
