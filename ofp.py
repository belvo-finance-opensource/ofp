from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import requests
import typer
from rich import box, print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from thefuzz import fuzz
from typing_extensions import Annotated


class Role(Enum):
    CONTA = "CONTA"
    DADOS = "DADOS"
    PAGTO = "PAGTO"
    CCORR = "CCORR"
    CDTCAR = "CDTCAR"
    CDTFIN = "CDTFIN"
    CDTPES = "CDTPES"
    CDTROV = "CDTROV"
    CDTIMB = "CDTIMB"
    CDTINV = "CDTINV"
    CDTCAP = "CDTCAP"
    CDTGCR = "CDTGCR"
    INVTIT = "INVTIT"
    INVFUN = "INVFUN"
    INVCRI = "INVCRI"
    INVCRA = "INVCRA"
    INVDEB = "INVDEB"
    INVACOE = "INVACOE"
    INVDER = "INVDER"
    INVPREV = "INVPREV"
    INVCAP = "INVCAP"
    INVFII = "INVFII"


app = typer.Typer()


def fetch_data():
    """Fetch data from the Open Finance Brazil directory"""
    url = "https://data.directory.openbankingbrasil.org.br/participants"
    response = requests.get(url)
    return response.json()


def find_participant(data: list, search_term: str) -> list:
    """Find participant by any unique identifier"""
    # Map of JSON fields that should return unique results
    unique_fields = {
        "OrganisationId": "Organization ID",
        "OrganisationName": "Organization Name",
        "RegistrationNumber": "Registration Number (CNPJ)",
        "RegistrationId": "Registration ID (ISPB)",
    }

    # First try direct fields
    for field, field_name in unique_fields.items():
        results = [org for org in data if org.get(field) == search_term]
        if results:
            if len(results) > 1:
                typer.echo(
                    f"Warning: Found multiple participants with {field_name}={search_term}. "
                    "This should not happen.",
                    err=True,
                )
            return results

    # Then try AuthorisationServerId
    results = [
        org
        for org in data
        if any(
            server.get("AuthorisationServerId") == search_term
            for server in org.get("AuthorisationServers", [])
        )
    ]
    if results:
        if len(results) > 1:
            typer.echo(
                f"Warning: Found multiple participants with AuthorisationServerId={search_term}. "
                "This should not happen.",
                err=True,
            )
        return results

    # If no exact matches found, try fuzzy search
    return fuzzy_search_participants(data, search_term)


def format_date(date_str: str) -> str:
    """Convert ISO date string to a more readable format"""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except (ValueError, AttributeError):
        return date_str


def print_participant(participant: dict, auth_server_id: Optional[str] = None):
    """Print participant information in a structured format"""
    console = Console()

    # Always show organization details
    console.print(
        Panel(
            f"[bold white]{participant['OrganisationName']}[/bold white]\n"
            f"[white]{participant['OrganisationId']}[/white]",
            title="Organization Details",
            border_style="green",
        )
    )

    # Always show basic information
    basic_info = Table(show_header=False, box=box.SIMPLE)
    basic_info.add_column("Field", style="bold white")
    basic_info.add_column("Value", style="bright_white dim")

    basic_fields = [
        ("Status", participant["Status"]),
        ("Legal Entity Name", participant["LegalEntityName"]),
        ("Registration Number (CNPJ)", participant["RegistrationNumber"]),
        ("Registration ID (ISPB)", participant["RegistrationId"]),
        ("Created On", format_date(participant["CreatedOn"])),
    ]

    for field, value in basic_fields:
        if value:
            basic_info.add_row(field, str(value))

    console.print(Panel(basic_info, title="Basic Information", border_style="green"))

    # Always show roles claims
    if participant.get("OrgDomainRoleClaims"):
        roles_table = Table(box=box.SIMPLE)
        roles_table.add_column("Role", style="bold white")
        roles_table.add_column("Status", style="bright_white")
        roles_table.add_column("Domain", style="bright_white")
        roles_table.add_column("Registration ID", style="bright_white")

        for claim in participant["OrgDomainRoleClaims"]:
            roles_table.add_row(
                claim["Role"],
                claim["Status"],
                claim["AuthorisationDomain"],
                claim["RegistrationId"],
            )

        console.print(Panel(roles_table, title="Role Claims", border_style="green"))

    auth_servers = participant.get("AuthorisationServers", [])

    if auth_server_id:
        if auth_servers:
            server = next(
                (
                    s
                    for s in auth_servers
                    if s["AuthorisationServerId"] == auth_server_id
                ),
                None,
            )
            if server:
                print_auth_server_details(console, server)
        return

    # Show authorization servers summary when no specific server is requested
    if auth_servers:
        summary_table = Table(box=box.SIMPLE)
        summary_table.add_column("Name", style="bold white")
        summary_table.add_column("Server ID", style="bright_white")
        summary_table.add_column("Status", style="bright_white")
        summary_table.add_column("API Families", style="bright_white")

        for server in auth_servers:
            api_families = set(
                api["ApiFamilyType"] for api in server.get("ApiResources", [])
            )
            summary_table.add_row(
                server["CustomerFriendlyName"],
                server["AuthorisationServerId"],
                server["Status"],
                "\n".join(sorted(api_families)) if api_families else "No APIs",
            )

        console.print(
            Panel(
                summary_table,
                title="🔐 Authorization Servers Summary",
                border_style="yellow",
            )
        )

        # Add callout about the --auth-server flag
        console.print(
            "\n[bold yellow]ℹ️  Tip:[/bold yellow] Use [cyan]--auth-server <ID>[/cyan] flag to see detailed information for a specific Authorization Server"
        )


def print_auth_server_details(console: Console, server: dict):
    """Print detailed information for a specific Authorization Server"""
    console.print("\n[bold yellow]🔐 Authorization Server Details[/bold yellow]")

    # Server Information
    console.print(
        Panel(
            f"[bold white]{server['CustomerFriendlyName']}[/bold white]\n"
            f"[bright_white]{server['CustomerFriendlyDescription']}[/bright_white]\n\n"
            f"[bold white]Server ID:[/bold white] [bright_white]{server['AuthorisationServerId']}[/bright_white]\n"
            f"[bold white]Status:[/bold white] [bright_white]{server['Status']}[/bright_white]\n"
            f"[bold white]Developer Portal:[/bold white] [bright_white]{server['DeveloperPortalUri']}[/bright_white]\n\n"
            f"[bold white]OpenID Configuration:[/bold white] [bright_white]{server['OpenIDDiscoveryDocument']}[/bright_white]\n"
            f"[bold white]Issuer:[/bold white] [bright_white]{server['Issuer']}[/bright_white]\n"
            f"[bold white]Payload Signing Cert Location:[/bold white] [bright_white]{server['PayloadSigningCertLocationUri']}[/bright_white]\n\n"
            f"[bold white]Supports DCR:[/bold white] {'✅' if server['SupportsDCR'] else '❌'}\n"
            f"[bold white]Supports CIBA:[/bold white] {'✅' if server['SupportsCiba'] else '❌'}\n"
            f"[bold white]Supports Redirect:[/bold white] {'✅' if server['SupportsRedirect'] else '❌'}",
            title="Server Information",
            border_style="yellow",
        )
    )

    # API Resources
    if server.get("ApiResources"):
        console.print("\n[bold yellow]📚 Available APIs[/bold yellow]")

        for api in server["ApiResources"]:
            # Create a table for all API information
            api_info = Table(show_header=False, box=box.SIMPLE)
            api_info.add_column("Field", style="bold white")
            api_info.add_column("Value", style="bright_white")

            # Basic API information
            api_info.add_row("Family Type", api["ApiFamilyType"])
            api_info.add_row("Version", f"v{api['ApiVersion']}")
            api_info.add_row("Status", api["Status"])
            api_info.add_row("Resource ID", api["ApiResourceId"])
            api_info.add_row("Family Complete", "✅" if api["FamilyComplete"] else "❌")

            # Certification information
            api_info.add_row("Certification Status", api["CertificationStatus"])
            if api["CertificationStartDate"]:
                api_info.add_row("Certification Start", api["CertificationStartDate"])
            if api["CertificationExpirationDate"]:
                api_info.add_row(
                    "Certification Expiration", api["CertificationExpirationDate"]
                )
            if api.get("ApiCertificationUri"):
                api_info.add_row(
                    "Certification URI",
                    f"[link={api['ApiCertificationUri']}]{api['ApiCertificationUri']}[/link]",
                )

            # Endpoints
            if api.get("ApiDiscoveryEndpoints"):
                endpoints = "\n".join(
                    f"{endpoint['ApiEndpoint']}\nID: {endpoint['ApiDiscoveryId']}"
                    for endpoint in api["ApiDiscoveryEndpoints"]
                )
                api_info.add_row("Endpoints", endpoints)

            # Display the API panel
            console.print(
                Panel(
                    api_info,
                    title=f"🔌 {api['ApiFamilyType']} API",
                    border_style="yellow",
                )
            )


def fuzzy_search_participants(data: List[dict], search_term: str) -> List[Dict]:
    """Search participants using fuzzy matching on names"""
    matches = []
    search_term = search_term.lower()

    for org in data:
        # Check OrganisationName, LegalEntityName and CustomerFriendlyDescription
        org_name = org.get("OrganisationName", "").lower()
        legal_name = org.get("LegalEntityName", "").lower()

        # Get CustomerFriendlyDescription from all auth servers
        descriptions = []
        for server in org.get("AuthorisationServers", []):
            if desc := server.get("CustomerFriendlyDescription"):
                descriptions.append(desc.lower())

        name_ratio = fuzz.partial_ratio(search_term, org_name)
        legal_ratio = fuzz.partial_ratio(search_term, legal_name)

        # Check descriptions with higher threshold
        desc_ratio = 0
        for desc in descriptions:
            desc_ratio = max(desc_ratio, fuzz.partial_ratio(search_term, desc))
            if (
                desc_ratio >= 90
            ):  # If we find a good description match, no need to check others
                break

        if name_ratio > 75 or legal_ratio > 75 or desc_ratio >= 90:
            matches.append(
                {"score": max(name_ratio, legal_ratio, desc_ratio), "org": org}
            )

    # Sort by match score and get top 10
    matches.sort(key=lambda x: x["score"], reverse=True)
    return [m["org"] for m in matches[:10]]


def display_search_results(participants: List[dict]) -> Optional[str]:
    """Display search results and let user select one"""
    if not participants:
        return None

    console = Console()
    table = Table(show_header=True)
    table.add_column("Index", style="cyan")
    table.add_column("Organization Name", style="white")
    table.add_column("Legal Name", style="white")
    table.add_column("Organization ID", style="bright_white dim")

    for idx, participant in enumerate(participants, 1):
        table.add_row(
            str(idx),
            participant["OrganisationName"],
            participant["LegalEntityName"],
            participant["OrganisationId"],
        )

    console.print("\nFound the following matches:")
    console.print(table)

    while True:
        choice = typer.prompt("\nSelect an organization (number) or 'q' to quit")
        if choice.lower() == "q":
            raise typer.Exit()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(participants):
                return participants[idx]["OrganisationId"]
            else:
                console.print("[red]Invalid selection. Please try again.[/red]")
        except ValueError:
            console.print("[red]Please enter a valid number or 'q' to quit.[/red]")


@app.command()
def main(
    search: Annotated[
        Optional[str],
        typer.Option(
            "--search",
            help="Search by Organization ID, Name, Registration Number (CNPJ), Registration ID (ISPB), or fuzzy name matching",
        ),
    ] = None,
    role: Annotated[
        Optional[Role],
        typer.Option(
            help="Filter by role",
            case_sensitive=False,
        ),
    ] = None,
    auth_server: Annotated[
        Optional[str],
        typer.Option(
            help="Show detailed information for a specific Authorization Server ID"
        ),
    ] = None,
    json: bool = typer.Option(False, "--json", help="Print raw JSON output"),
):
    """Visualize information about Open Finance Participants"""
    console = Console(stderr=True)

    try:
        data = fetch_data()
    except requests.RequestException as e:
        console.print(f"[bold red]Error:[/bold red] Error fetching data: {e}")
        raise typer.Exit(code=1)

    # Handle search
    if search:
        matches = find_participant(data, search)
        if not matches:
            console.print(f"[bold red]Error:[/bold red] No matches found for: {search}")
            raise typer.Exit(1)

        # If we got multiple matches (from fuzzy search), show selection
        if len(matches) > 1:
            selected_org_id = display_search_results(matches)
            if not selected_org_id:
                raise typer.Exit()
            # Get the specific organization data
            data = find_participant(data, selected_org_id)
        else:
            data = matches

    # Handle auth server
    if auth_server:
        for participant in data:
            for server in participant.get("AuthorisationServers", []):
                if server["AuthorisationServerId"] == auth_server:
                    if json:
                        print_json(data=server)  # Print just the auth server JSON
                    else:
                        print_participant(participant, auth_server)
                    return

        console.print(
            f"[bold red]Error:[/bold red] Authorization Server ID '{auth_server}' not found"
        )
        raise typer.Exit(1)

    # Process role filter
    if role:
        data = [
            org
            for org in data
            if any(
                claim.get("Role") == role.value
                for claim in org.get("OrgDomainRoleClaims", [])
            )
        ]

        if not data:
            console.print(
                f"[bold red]Error:[/bold red] No participants found with role={role.value}"
            )
            raise typer.Exit(1)

    # Warn about printing all participants only if no filters are applied and not JSON
    if not any([search, role, auth_server]) and not json:
        participant_count = len(data)
        console.print(
            f"\n[bold yellow]Warning:[/bold yellow] You are about to print information for [bold]{participant_count}[/bold] participants."
        )
        console.print("This will generate a lot of output.")
        console.print("\nConsider using filters to narrow down the results:")
        console.print(
            "  • Search by organization name/ID or registration number/ID: python ofp.py --search <term>"
        )
        console.print("  • Filter by role: python ofp.py --role <ROLE>")
        console.print("  • Get specific auth server: python ofp.py --auth-server <ID>")

        if not typer.confirm("\nDo you want to continue?"):
            raise typer.Exit()

        console.print()  # Add a blank line before output

    if json:
        print_json(data=data)
    else:
        for participant in data:
            print_participant(participant, auth_server)


if __name__ == "__main__":
    app()
