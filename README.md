# Open Finance Participants CLI

A command-line tool to explore and debug Open Finance Participants information. Easily search for participants, check their roles, and inspect Authorization Server details.

## Requirements

- Python 3.13+
- uv (<https://docs.astral.sh/uv/>)

## Installation

1. Clone the repository:

```bash
   git clone https://github.com/belvo-finance-opensource/ofp.git
   cd ofp  
```

2. Create a virtual environment:

```bash
   uv venv
```

3. Sync project dependencies:

```bash
   uv sync
```

4. Install the project and make the CLI available globally (optional):

```bash
   uv pip install -e .
```

## Usage

### Basic Command Structure

If you installed the project, you can use the CLI directly:

```bash
   ofp [OPTIONS]
```

If you didn't install the project, you can use the CLI by running:

```bash
   python -m ofp [OPTIONS]
```

Use `ofp --help` to see all available options.

## Example Commands

1. **List all participants** (will ask for confirmation):

```bash
   ofp
```

2. **Search by Organization Name** (fuzzy match):

```bash
   ofp --search itau
```

3. **Search by Registration ID (ISPB)**:

```bash
   ofp --search 60701190
```

4. **Search by Registration Number (CNPJ)**:

```bash
   ofp --search 60701190000104
```

5. **Search by Organisation ID**:

```bash
   ofp --search 9c721898-9ce0-50f1-bf85-05075557850b
```

6. **Filter by directory Role**:

```bash
   ofp --role DADOS
```

7. **Get detailed API information for an specific Authorization Server**:

```bash
   ofp --auth-server 68308291-ec0d-4398-83ce-68b6b1087e49
```

8. **Get JSON output** (useful for scripting):

```bash
   ofp --json
```

## Output

The tool provides **formatted output** with the following details:

- **Organization Details**:
  - Basic information
  - Role Claims
- **Authorization Servers**:
  - Summary or detailed API information

### Example

![ofp-cli-output](./assets/images/cli_output_rich.png)

## Tips

- Always try to use `--search` to narrow down results.
- Use `--auth-server` when you need detailed API information.
- Use `--json` for programmatic (raw) access to the data.
