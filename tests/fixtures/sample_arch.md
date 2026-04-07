# Architecture

## Layer Dependency Rules

```layers
Layer 0: internal/types/, pkg/models/        -> Pure type definitions, no internal imports
Layer 1: internal/utils/                     -> Utility functions, depends on Layer 0 only
Layer 2: internal/config/                    -> Configuration, depends on Layer 0-1
Layer 3: internal/services/, internal/core/  -> Business logic, depends on Layer 0-2
Layer 4: cmd/, api/handlers/                 -> Interface layer, depends on Layer 0-3, no mutual imports
```

## Quality Rules

```quality
max_file_lines: 500
forbidden_patterns: fmt.Println, console.log, print(
naming_files: snake_case
naming_types: PascalCase
```
