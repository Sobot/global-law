# Global law

**Global law** is a read-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for exploring legal texts and their history across jurisdictions. Ask an AI assistant for a provision, the text that was in force on a particular date, the change that introduced it, or a comparison between versions—and receive Git-backed references to the underlying text and changes.

The hosted server is available at:

```text
https://global-law.lexifina.com/mcp
```

It uses Streamable HTTP, requires no account or API key, and does not modify the corpus or make outbound calls. It is designed for research and source discovery; its answers are not legal advice.

## What it can do

- Find provisions by citation, title, words, or short phrases.
- Read a provision as it existed on a specified date.
- Compare versions and identify what changed.
- Trace the commits, authors, publication references, and source links behind a provision.
- Resolve legal citations and link directly to the relevant corpus files and diffs.
- Search the jurisdictions and bodies of law available to the server.
- Expose guidance for citing provisions, checking historical validity, and comparing versions.

The server exposes 18 read-only tools. Every tool is annotated as non-destructive and idempotent. The hosted deployment refreshes its public corpus twice daily and applies request limits to protect availability.

## Example questions

- `How did Article 21 of the Serbian Code of Criminal Procedure read on 29 May 2019? Include the source.`
- `Compare the versions of this provision on 28 and 29 May 2019 and show only the changes.`
- `Which amendment introduced the change published in Official Gazette RS No. 35/2019?`
- `Find the provisions about termination of a contract in French law and link to the source text.`

For reliable historical results, include the jurisdiction and the date you care about. If the requested history is not present in the selected corpus, the answer should state that boundary rather than infer the law.

## Connect a client

Add a remote MCP server with the URL above. No authentication is required.

### Claude

Open **Customize → Connectors → Add custom connector**, enter the URL, choose **No sign in**, and add it to a chat.

### ChatGPT

Open the custom MCP server/plugin setup, enter the URL, choose no authentication, and enable the server in a new chat. Availability depends on the account or workspace plan.

### Local MCP clients

For clients that support a JSON configuration, use:

```json
{
  "mcpServers": {
    "global-law": {
      "url": "https://global-law.lexifina.com/mcp"
    }
  }
}
```

Client-specific installation instructions and the complete protocol reference are in [MCP.md](MCP.md).

## Run it locally

A local checkout needs Git, Python 3.9 or newer, and the legal corpus you want to query. The server uses the repository and Git history directly; it has no third-party runtime dependencies.

```sh
git clone --recurse-submodules https://github.com/Sobot/global-law.git
cd global-law
sh tools/mcp.sh
```

To download only selected jurisdictions, use the country helper before starting the server:

```sh
python3 tools/countries.py add france spain
```

The repository contains client configuration, shared tools, tests, and country corpora as Git submodules. See [MCP.md](MCP.md) for deployment details and [FEATURES.md](FEATURES.md) for the shared command-line features.

## Important limitations

- Corpus coverage and history depend on the jurisdiction repositories and the checkout or hosted deployment being queried.
- “Nothing found” means nothing was found in the searched corpus; it does not mean that no such law exists.
- Search results and historical answers should be checked against the linked source text.
- The service provides legal information and references, not legal advice or a determination of anyone’s rights.
- Public, unauthenticated access should be used responsibly and within the service limits.

## Project status

The project is preparing the hosted server for publication in the ChatGPT Apps Directory and Anthropic Claude Connectors Directory. The submission checklist is tracked in [issue #30](https://github.com/Sobot/global-law/issues/30), including domain verification, public legal and support pages, tool-description review, starter prompts, test scenarios, and final smoke testing.

## Related documentation

- [MCP server reference and client setup](MCP.md)
- [Feature reference](FEATURES.md)
- [Serbian deployment and search documentation](README.serbia.md)
- [Contribution guide](CONTRIBUTING.md)
- [License](LICENSE.md)

## Origin and license

This repository is a deployment of the [Global Law](https://github.com/lexifina/global-law) project, using jurisdiction-specific legal corpora such as [Serbia law](https://github.com/lexifina/serbia-law). The repository is released under [CC0](LICENSE.md). Individual legal corpora may have additional terms described in their source repositories.
