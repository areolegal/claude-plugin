# The CLM code (`from clm import ...`) lives in the skill's scripts folder; clm_paths puts it on sys.path,
# so the suite runs both from plugin/ (`pytest tests`) and from tests/clm.
import clm_paths  # noqa: F401
