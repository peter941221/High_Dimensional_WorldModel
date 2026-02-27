# Kaggle Runner Files

- `run_kaggle_job.py`: Kaggle kernel entry script.
- `run_config.example.json`: configuration template for batch runs.
- `kernel-metadata.template.json`: metadata template reference.

The generated build bundle writes a runtime config to:

```text
kaggle/run_config.json
```

You normally do not edit this manually when using:

```bash
python kaggle_job_manager.py prepare ...
python kaggle_job_manager.py run ...
```
