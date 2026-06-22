# Name portability

The project is currently codenamed **Zorn**, but the scaffold treats the name as presentation/configuration rather than domain logic.

## Rules

- Use `C2_COMPAT_` as the environment prefix.
- Keep the Python package neutral: `zorn`.
- Keep public REST paths compatibility-focused: `/api/v1/...`.
- Put display names in `AppSettings.product_name`.
- Do not bake the codename into database table names.
- Do not bake the codename into event names.
- Use docs and README language that says "currently codenamed" until the name is final.

## Rename checklist

To rename the project before a public release:

1. Change `C2_COMPAT_PRODUCT_NAME` in deployment config.
2. Rename the repository.
3. Optionally rename the package and console script.
4. Update README branding.
5. Keep compatibility paths stable.
