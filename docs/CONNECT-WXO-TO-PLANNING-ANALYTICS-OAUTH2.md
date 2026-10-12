# Configuring the Integration Between watsonx Orchestrate and IBM Planning Analytics via OAuth 2.0

## Overview

This guide walks you through the full end-to-end setup of the **OAuth 2.0-authenticated** integration between **IBM watsonx Orchestrate** and **IBM Planning Analytics on Cloud**. OAuth 2.0 is used both to authorise watsonx Orchestrate's access to the Planning Analytics MCP server and to secure the embedded chat widget inside Planning Analytics Workspace. The integration works in two complementary directions:

### Integration Architecture

```mermaid
flowchart TB
    subgraph DIR1["Direction 1 — Orchestrate → Planning Analytics (MCP)"]
        direction LR
        Agent["Planning Analytics Agent\n(watsonx Orchestrate)"]
        MCP["Planning Analytics\nMCP Server\n/api/v0/agentic-ai/ibm-pa-tools/mcp"]
        TM1["Planning Analytics\nWorkspace (TM1)"]

        Agent -- "OAuth2 + MCP\n(Streamable HTTP)" --> MCP
        MCP -- "41 PA Tools\n(TM1 REST API)" --> TM1
    end

    subgraph DIR2["Direction 2 — Embedded Chat within Planning Analytics"]
        direction LR
        PAW["Planning Analytics\nWorkspace"]
        Embed["Embedded Chat Widget\n(iframe)"]
        WxO["watsonx Orchestrate Agent\n(secure embed / JWT)"]

        PAW --> Embed
        Embed -- "HTTPS + JWT" --> WxO
    end
```

**Direction 1 — Sections 1 & 2:** watsonx Orchestrate connects **to** Planning Analytics through the Planning Analytics MCP Server. An Orchestrate agent calls the 41 Planning Analytics tools (TM1 cube reads, writes, views, processes, and more) exposed over the MCP Streamable HTTP protocol, authenticated via OAuth2.

**Direction 2 — Section 3:** A watsonx Orchestrate-powered chat is embedded **inside** Planning Analytics Workspace via a secure iframe. Users interact with the AI assistant directly from within the Planning Analytics UI, without leaving the application.

### Reference Documentation

- [Configuring the integration with an agentic chat](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=integrations-configuring-integration-agentic-chat)
- [Configure Model Provider for Planning Analytics Agent Features](https://www.ibm.com/docs/en/planning-analytics/2.1.0?topic=workspace-configure-model-provider-planning-analytics-agent-features)
- [Configuring security for embedded chat (watsonx Orchestrate)](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=chat-configuring-security-embedded)

---

## Prerequisites

- Access to an IBM Planning Analytics on Cloud instance
- Admin access to that Planning Analytics instance
- An IBM Cloud account with an active **watsonx Orchestrate** instance (this guide uses the `eu-de` / Frankfurt region as an example)
- Admin rights to the watsonx Orchestrate instance
- Ability to register an **OAuth 2.0 client** in the Planning Analytics Administration → Integrations panel (required for both directions)

---

## Section 1 — Set Up the Connection from Orchestrate to Planning Analytics

This section establishes the OAuth2-authenticated MCP connection from watsonx Orchestrate to Planning Analytics. By the end you will have a registered MCP server in Orchestrate exposing all 41 Planning Analytics tools.

### Step 1 — Log in to your Planning Analytics instance

Open a browser and navigate to your Planning Analytics on Cloud URL (e.g. `https://your-instance.planning-analytics.cloud.ibm.com`). Log in with your credentials.

You land on the **Home / Welcome** page of your Planning Analytics tenant.

![Step 1 — Planning Analytics Home](../assets/pa-setup-procedure-1.png)

> The tenant in this example is **your Planning Analytics instance** (non-production environment). The four Quick Launch tiles — *Applications and Plans*, *Reports and Analysis*, *Data and Models*, and **Administration** — are visible on the home page.

---

### Step 2 — Open the Administration menu

Click the **hamburger menu (☰)** icon in the top-left orange navigation bar to open the left sidebar.

In the sidebar, hover over **Administration** (gear icon) at the bottom of the list.

![Step 2 — Hamburger menu with Administration highlighted](../assets/pa-setup-procedure-2.png)

> Click **Administration** to navigate to the administration section.

---

### Step 3 — Navigate to Integrations

You are now on the **Administration** dashboard, which shows a summary of your environment (databases, users, and groups) along with a set of quick-access tiles.

Click the **Integrations** tile (bottom-left, with a monitor icon).

![Step 3 — Administration dashboard with Integrations tile](../assets/pa-setup-procedure-3.png)

> The Integrations tile description reads: *"Manage Planning Analytics Integrations with other products and services."*

---

### Step 4 — Create an OAuth Client

On the **Integrations** page, the left panel lists the available integrations:

| Integration | Status |
|---|---|
| IBM watsonx AI Jobs | Inactive |
| IBM watsonx Orchestrate | Active |
| **OAuth client** | N/A |

Click **OAuth client** in the left panel.

The right panel shows the OAuth client list, which is empty on a fresh setup. Click **Add** to create a new client and give it a meaningful name (e.g. `pa-oauth-client`).

Once created, the client row appears in the table. Make a note of both values — you will need them in Step 10:

> - **Client ID** — displayed in the table (e.g. `1b86****-****-****-****-****eaf5707a`)
> - **Client Secret** — shown only once at creation time; copy it immediately and store it securely

![Step 4 — OAuth Client section showing a newly created client](../assets/pa-setup-procedure-4.png)

---

### Step 5 — Configure the Redirect URL for watsonx Orchestrate

Click the **three-dot menu (⋮)** on the OAuth client row and choose **Edit**. The **Edit client** dialog opens.

In the **Redirect URLs** section, click **Add +** and enter the watsonx Orchestrate callback URL for your region:

```
https://eu-de.watson-orchestrate.cloud.ibm.com/mfe_callback
```

> Adjust the region prefix (`eu-de`) to match your Orchestrate deployment region (e.g. `us-south`, `eu-gb`).

Click **Save** when done.

![Step 5 — Edit client dialog with Redirect URL added](../assets/pa-setup-procedure-5.png)

> The screenshot shows additional URLs (Postman, localhost) that may be present in an existing environment. These are not required for this integration and can be ignored.

---

### Step 6 — Log in to IBM Cloud

Open a new browser tab and navigate to [https://cloud.ibm.com](https://cloud.ibm.com). Log in with your IBMid.

Make sure the correct **account** is selected in the top navigation bar (e.g. `<your-account-id> - <your-org>`).

![Step 6 — IBM Cloud Dashboard](../assets/pa-setup-procedure-6.png)

---

### Step 7 — Find your watsonx Orchestrate instance in the Resource List

In the IBM Cloud left navigation rail, click **Resource list** (or go directly to `cloud.ibm.com/resources`).

Expand the **AI / Machine Learning** category. Your watsonx Orchestrate instance should appear:

| Name | Group | Location | Product | Status |
|---|---|---|---|---|
| `watsonx Orchestrate-<your-instance>` | <your-resource-group> | Frankfurt (eu-de) | watsonx Orchestrate | ✅ active |

![Step 7 — Resource list showing watsonx Orchestrate instance](../assets/pa-setup-procedure-7.png)

> If the instance is not visible or not active, confirm you are viewing the correct account and region.

---

### Step 8 — Open the watsonx Orchestrate instance management page

Click on the **`watsonx Orchestrate-<your-instance>`** instance name to open its management page.

The management page displays:
- The instance name and status (active, green checkmark)
- A **`Launch watsonx Orchestrate`** primary button
- A Credentials section (API key and instance URL)
- Current plan information

![Step 8 — watsonx Orchestrate instance management page](../assets/pa-setup-procedure-8.png)

---

### Step 9 — Launch watsonx Orchestrate

Click the blue **`Launch watsonx Orchestrate`** button.

This opens the watsonx Orchestrate application in a new tab (`eu-de.watson-orchestrate.cloud.ibm.com/home`). You land on the **Home Dashboard** showing agent metrics and operational health.

In the left sidebar, locate the **GOVERN & OPERATE** section and click **Connections**.

![Step 9 — watsonx Orchestrate Home Dashboard](../assets/pa-setup-procedure-9.png)

---

### Step 10 — Create and configure the connection for Planning Analytics (NP)

From the left sidebar, click **Connections** under **GOVERN & OPERATE**. This opens the **Security control center** on the **Connections** tab.

Click **Add connection +**, select **Custom connection**, and name it `pa-connection`.

The connection dialog opens on the **Draft** tab. Fill in the following fields:

| Field | Value |
|---|---|
| SSO | Off |
| Authentication type | `OAuth2 Authorization Code` |
| Token URL | `https://your-instance.planning-analytics.cloud.ibm.com/oauth2/token` |
| Authorization URL | `https://your-instance.planning-analytics.cloud.ibm.com/oauth2/authorize` |
| Client ID | `1b86****-****-****-****-****eaf5707a` |
| Client Secret | `ddf3****************************************************3ca52ce` |
| Scope (optional) | `v0UserContext` |

> **Important:** The **Callback URL** at the bottom of the form is auto-generated by Orchestrate (e.g. `https://eu-de.watson-orchestrate.cloud.ibm.com/mfe_connectors/api/v1/agentic/oauth/_callback`). Copy this value and return to Step 5 to add it as an additional Redirect URL in your Planning Analytics OAuth client if you have not already done so.

![Step 10 — Draft connection configuration form](../assets/pa-setup-procedure-10.png)

> The screenshot shows a connection that has already been saved. On a fresh setup the form will be blank — fill in the values from the table above before saving.

---

### Step 11 — Configure the Live connection

Switch to the **Live** tab of the `pa-connection` dialog.

Click **`Paste draft configuration`** to copy all settings from the Draft tab into the Live tab. Verify that all fields are populated identically.

![Step 11 — Live tab with Paste draft configuration button](../assets/pa-setup-procedure-11.png)

---

### Step 12 — Save and verify the connection

Click **Save**. You may be prompted to authenticate against the Planning Analytics server to approve the OAuth connection — follow the on-screen prompts.

Back on the **Security control center — Connections** page, the new `pa-connection` entry appears under the **Custom** filter tab. Confirm that both columns are populated:
- **Draft:** OAuth2 (Authorization Code) / Team credentials
- **Live:** OAuth2 (Authorization Code) / Team credentials

![Step 12 — Connections list showing pa-connection active in both Draft and Live](../assets/pa-setup-procedure-12.png)

> The screenshot shows "Custom (1)" because one connection exists. On a fresh environment this will be your first and only entry.

---

### Step 13 — Navigate to MCP Servers

In the left sidebar, scroll down to the **AI GATEWAY** section and click **MCP servers**.

![Step 13 — Navigation to MCP Servers under AI Gateway](../assets/pa-setup-procedure-13.png)

> The AI GATEWAY section is labelled **Preview**. MCP server functionality may change before general availability.

---

### Step 14 — Open the Register MCP Server form

On the **MCP servers** page, click **Register server +** in the top-right corner.

The **Register MCP server** form opens. Fill in the following fields:

| Field | Value |
|---|---|
| **Server name** (required) | `ibm-pa-tools` |
| **Transport type** (required) | `Streamable HTTP` |
| **MCP server URL** (required) | `https://your-instance.planning-analytics.cloud.ibm.com/api/v0/agentic-ai/ibm-pa-tools/mcp` |
| **Connection** (optional) | `pa-connection` |
| **Description** | *(optional)* e.g. `Planning Analytics NP environment — 41 PA tools` |

![Step 14 — Register MCP Server form](../assets/pa-setup-procedure-14.png)

Click **Register** to submit.

---

### Step 15 — Verify the MCP Server registration (41 tools)

After clicking **Register**, Orchestrate connects to the MCP server and auto-discovers all available tools. This may take **1–2 minutes**.

Once complete, the **MCP servers** dashboard shows:
- **Servers:** 1 (or more, if you have registered additional servers previously)
- **Tools:** 41

Expand the `ibm-pa-tools` row to view the full list of 41 Planning Analytics tools, including:
- `get_tm1_metrics`
- `get_saved_view`
- `get_cube_annotations`
- `delete_tm1_process`
- … and 37 more

![Step 15 — MCP servers dashboard showing 1 server and 41 tools](../assets/pa-setup-procedure-15.png)

> ✅ **Section 1 complete.** The connection from watsonx Orchestrate to Planning Analytics via the MCP server is now established.

---

## Section 2 — Create a Planning Analytics Agent in Orchestrate

In this section, you create a Planning Analytics agent in watsonx Orchestrate. You start from a pre-built IBM catalog template, replace its placeholder tools with your own MCP server tools, and deploy the agent to production.

### Step 16 — Open the Catalog and search for Planning Analytics agents

From the left sidebar, click **Catalog** under **BUILD & RUN**.

In the Catalog search bar, type **`Planning`**. The results filter to show agents and MCP servers related to Planning Analytics.

Two IBM-native agents are available out of the box:

| Agent | Description |
|---|---|
| **Planning Analytics Manager** | Orchestrates seamless financial planning and allocation workflows in IBM Planning Analytics |
| **Planning Analytics Allocation Agent** | Manages allocation workflows within an IBM Planning Analytics instance |

![Step 16 — Catalog filtered on "Planning" showing PA agents](../assets/pa-setup-procedure-16.png)

---

### Step 17 — Select the Planning Analytics Allocation Agent

Click the **Planning Analytics Allocation Agent** card to open its detail page.

The overview shows the agent's description, its artifact hierarchy (15 tools connected by default), version, and publisher information. Two actions are available in the top-right:
- **Use as template** — creates a new editable agent based on this one
- **Add to Agent** — adds this agent as a sub-agent to an existing agent

Click **Use as template** to create your own copy.

![Step 17 — Planning Analytics Allocation Agent catalog detail page](../assets/pa-setup-procedure-17.png)

> The 15 tools in the artifact hierarchy are catalog placeholders tied to IBM-provided tool definitions — not your local instance. You will replace them in the next steps.

---

### Step 18 — Customise the agent name and description

After clicking **Use as template**, the agent editor opens on the **Behavior** tab. Update the agent profile to reflect your environment:

- **Agent name** — give it a meaningful name (e.g. `Planning Analytics Orchestrator`)
- **Model** — select the LLM to use (e.g. `GPT-OSS 120B — OpenAI via Groq`)
- **Description** — describe the agent's purpose and scope
- **Instructions** — write the system prompt that governs the agent's behaviour

The **Draft Preview** panel on the right updates in real time as you edit, so you can immediately test the greeting and instructions.

![Step 18 — Agent editor Behavior tab with name and description filled in](../assets/pa-setup-procedure-18.png)

> The screenshot shows an agent configured in French for your environment. Adapt the name, description, and instructions to your own context and language.

---

### Step 19 — Navigate to the Tools tab and remove the placeholder tools

Click the **Tools** tab in the agent editor (alongside Behavior, Knowledge, and Agents).

The template comes pre-wired with 15 catalog tools pointing to IBM's sample Planning Analytics instance. These are placeholders that must be removed before you can add tools from your own MCP server.

Select all existing tools and remove them until the list is empty.

![Step 19 — Tools tab empty after removing all placeholder tools](../assets/pa-setup-procedure-19.png)

> On a fresh template the list shows 15 entries. The screenshot shows it already empty because this step was completed before the screenshot was taken.

---

### Step 20 — Add tools from your local instance

With the tools list empty, click **Add Tool +**.

The **Add a tool** modal opens. Under the **Add from** section, click **MCP server**.

![Step 20 — "Add a tool" modal with MCP server option visible](../assets/pa-setup-procedure-20.png)

---

### Step 21 — Search for tools from the ibm-pa-tools server

The tool picker modal opens, titled **Add tools to [your agent name]**.

In the search box, type **`ibm-pa-tools`** to filter the list to all tools exposed by your `ibm-pa-tools` MCP server. All 41 tools are displayed, each prefixed with `ibm-pa-tools:`.

Select the tools you want to give your agent access to, then click **Add to agent**.

![Step 21 — Tool picker filtered on "ibm-pa-tools" showing ibm-pa-tools tools](../assets/pa-setup-procedure-21.png)

> For a minimal test agent, start with a small set of relevant tools (e.g. `get_saved_view`, `get_tm1_metrics`, `execute_tm1_process`). You can always add more later.

---

### Step 22 — Test the agent in the Draft Preview

With tools added, use the **Draft Preview** panel on the right to send a test request to your agent. Try a query that exercises one of the newly added tools (e.g. ask it to list available TM1 servers or analyse a cube).

The agent should respond and invoke the appropriate tool from the `ibm-pa-tools` server. If debug mode is enabled, click **Show Reasoning** on any response to inspect the full tool call chain.

![Step 22 — Draft Preview showing a test query and agent response](../assets/pa-setup-procedure-22.png)

> The screenshot shows the agent responding in French and asking the user to clarify which TM1 server to target — the expected behaviour when the instructions prompt the agent to handle multiple servers.

---

### Step 23 — Go to the Deploy tab

Once you are satisfied with the agent's responses, click the **Deploy** tab in the top navigation bar (rocket icon).

You land on the **Draft Summary** view. Review the listed channels. When ready, click **Deploy to Live**.

![Step 23 — Deploy tab with Deploy to Live button](../assets/pa-setup-procedure-25.png)

---

### Step 24 — Create a version and deploy

The **Deploy agent version** modal opens. You must select a saved version of your agent to promote to Live.

If you have not yet saved a version, click **Create version +** (available from the top-right of the Build tab), give it a name and description, then return to the Deploy tab.

In the modal, select the version you want to deploy (e.g. `0.1.1 — Orchestrator`) and click **Deploy**.

![Step 24 — Deploy agent version modal with version selection](../assets/pa-setup-procedure-26.png)

---

### Step 25 — Copy the embedded agent snippet

Still on the **Deploy** tab, scroll down to the **Channels** section and expand the **Embedded agent** accordion.

Under **Embed on your website**, you will find a JavaScript snippet pre-populated with your agent's configuration:

```javascript
<script>
  window.wxOConfiguration = {
    orchestrationID: "<your-orchestration-id>",
    hostURL: "https://eu-de.watson-orchestrate.cloud.ibm.com",
    rootElementID: "root",
    deploymentPlatform: "ibmcloud",
    crn: "<your-crn>",
    chatOptions: {
      agentId: "<your-agent-id>",
    }
  };
  // ... loader script continues
</script>
```

Click the **copy to clipboard** icon in the top-right corner of the code box. Keep this snippet — you will paste values from it into the Planning Analytics configuration in Section 3.

![Step 25 — Deploy tab Embedded agent section with snippet and copy button](../assets/pa-setup-procedure-27.png)

---

### Step 26 — Navigate to Settings

Click your **user avatar** in the top-right of the Orchestrate header (showing your initials) to open the user menu.

Click **Settings**.

![Step 26 — User menu open with Settings option](../assets/pa-setup-procedure-28.png)

---

### Step 27 — Navigate to the Embed Security tab

On the Settings page, click the **Embed Security** tab in the horizontal tab bar.

![Step 27 — Settings page showing the Embed Security tab](../assets/pa-setup-procedure-29.png)

---

### Step 28 — Configure Embed Security with your public key

On the **Embed Security** tab, complete the following:

1. Ensure the **"Allow Builders to manage security settings"** toggle is **On**.
2. Ensure the **Security** toggle is **On** — this enables JWT-based authentication for the embedded chat.
3. Under **Chat user identity**, paste your **RSA public key** (PEM format, RS256) into the **Public key** text area.
4. Under **Encrypt sensitive information**, copy the **IBM provided public key** shown in the read-only field — you will need this value when configuring the Planning Analytics side.

![Step 28 — Embed Security tab with public key pasted in](../assets/pa-setup-procedure-30.png)

> This step requires a public/private RSA key pair. See Step 29 for how to generate one.

---

### Step 29 — Generate your RSA key pair

From a terminal, run the following commands to generate a 4096-bit RSA key pair:

```bash
# Generate the private key
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -out private-pa-key.pem

# Extract the public key from the private key
openssl rsa -in private-pa-key.pem -pubout -out public-pa-key.pem

# Copy the public key to clipboard → paste into watsonx Orchestrate (Step 28, "Chat user identity")
cat public-pa-key.pem | pbcopy

# Copy the private key to clipboard → paste into Planning Analytics configuration (Section 3)
cat private-pa-key.pem | pbcopy
```

![Step 29 — Embed Security tab with public key configured](../assets/pa-setup-procedure-31.png)

**Key usage summary:**

| Key | Where it goes |
|---|---|
| **Public key** (`public-pa-key.pem`) | Pasted into watsonx Orchestrate → Settings → Embed Security → **Chat user identity** |
| **Private key** (`private-pa-key.pem`) | Pasted into Planning Analytics → Features and Configuration → **Agentic Chat** |

> Reference: [Configuring security for embedded chat](https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=chat-configuring-security-embedded)

> ✅ **Section 2 complete.** The watsonx Orchestrate side of the integration is fully configured. You now have a live Planning Analytics agent with tools from your local MCP server, an embed snippet, and a secured public key. Continue to Section 3 to complete the configuration on the Planning Analytics side.

---

## Section 3 — Configure the Embedded Chat in Planning Analytics

In this section, you configure the Planning Analytics side to activate the embedded watsonx Orchestrate chat widget within Planning Analytics Workspace.

---

### Step 30 — Return to Planning Analytics Administration → Integrations

Go back to your Planning Analytics instance. From the hamburger menu, navigate to **Administration**, then click the **Integrations** tile.

You are back on the Integrations page. The left panel lists the three available integration types:

| Name | Status |
|---|---|
| IBM watsonx AI Jobs | Inactive |
| **IBM watsonx Orchestrate** | **Active** |
| OAuth client | N/A |

![Step 30 — Planning Analytics Administration Integrations page](../assets/pa-setup-procedure-32.png)

---

### Step 31 — Click on IBM watsonx Orchestrate

In the left panel, click **IBM watsonx Orchestrate**.

The right panel shows the integration configuration form. Select the **Custom instance** radio button.

The form reveals two fields:
1. **Configuration value** — a JSON editor for the agent connection parameters
2. **Embedded chat authorization key** — for the private RSA key

![Step 31 — IBM watsonx Orchestrate custom instance form](../assets/pa-setup-procedure-33.png)

---

### Step 32 — Build and paste the agent configuration JSON

Using the JavaScript snippet you copied in Step 25, extract the relevant values and build the following JSON object:

**Snippet reference (from the Orchestrate Deploy tab):**
```javascript
window.wxOConfiguration = {
  orchestrationID: "9a5d****************************156b-****-****-****-****887c9bed",
  hostURL: "https://eu-de.watson-orchestrate.cloud.ibm.com",
  crn: "crn:v1:bluemix:public:watsonx-orchestrate:eu-de:a/...",
  chatOptions: {
    agentId: "8a61****-****-****-****-****749277a",
    agentEnvironmentId: "9646****-****-****-****-****977b7a6",
  }
};
```

**JSON to paste into the Configuration value field:**
```json
{
  "purchaseID": "0077****63",
  "orchestrationID": "9a5d****************************156b-****-****-****-****887c9bed",
  "hostURL": "https://eu-de.watson-orchestrate.cloud.ibm.com",
  "agentId": "8a61****-****-****-****-****749277a",
  "agentEnvironmentId": "9646****-****-****-****-****977b7a6",
  "perspectives": [
    "pa-home",
    "pa-administration",
    "dashboard",
    "modeling",
    "modeling-home"
  ]
}
```

**Field mapping from snippet to JSON:**

| JSON field | Source in snippet | Notes |
|---|---|---|
| `purchaseID` | Not in snippet | Your IBM Planning Analytics purchase/contract ID |
| `orchestrationID` | `window.wxOConfiguration.orchestrationID` | Copy verbatim |
| `hostURL` | `window.wxOConfiguration.hostURL` | Copy verbatim |
| `agentId` | `window.wxOConfiguration.chatOptions.agentId` | Copy verbatim |
| `agentEnvironmentId` | `window.wxOConfiguration.chatOptions.agentEnvironmentId` | Copy verbatim |
| `perspectives` | Not in snippet | Controls which PA views display the chat widget |

The `perspectives` array determines in which Planning Analytics views the embedded chat widget appears. Available values are `pa-home`, `pa-administration`, `dashboard`, `modeling`, and `modeling-home`.

Paste the completed JSON into the **Configuration value** text area.

---

### Step 33 — Paste the private key

In the **Embedded chat authorization key** field, paste the **private key** (`private-pa-key.pem`) you generated in Step 29.

From your terminal:
```bash
cat private-pa-key.pem | pbcopy
```

Then paste (⌘V / Ctrl+V) into the **Embedded chat authorization key** field.

> Planning Analytics uses this private key to sign JWT tokens for every embedded chat request. watsonx Orchestrate uses the corresponding public key (registered in Step 28) to verify them — ensuring all embedded chat traffic is authenticated end-to-end.

---

### Step 34 — Fill in the watsonx.ai section

> ⚠️ **Note:** This section applies to **IBM Planning Analytics on Cloud v2.1.0** and is expected to be removed or simplified in a future release.

Below the agent configuration, the form contains a **watsonx.ai** section that requires a separate IBM Cloud credentials object. Paste the following JSON structure:

```json
{
  "watsonx_api_url": "https://eu-de.ml.cloud.ibm.com",
  "watsonx_api_key": "<your-watsonx-api-key>",
  "watsonx_api_project_id": "<your-watsonx-project-id>"
}
```

Steps 35–37 show you how to retrieve the three required values.

![Step 34 — IBM watsonx Orchestrate form showing agent config JSON and private key](../assets/pa-setup-procedure-33.png)

---

### Step 35 — Locate the watsonx.ai Runtime service and launch watsonx

Go to [https://cloud.ibm.com/resources](https://cloud.ibm.com/resources).

Expand the **AI / Machine Learning** category. You should see two entries:

| Name | Product | Status |
|---|---|---|
| `watsonx Orchestrate-<your-instance>` | watsonx Orchestrate | active |
| **`watsonx-ai-runtime`** | **watsonx.ai Runtime** | active |

Click **`watsonx-ai-runtime`** (the watsonx.ai Runtime instance).

![Step 35 — IBM Cloud Resource list showing watsonx-ai-runtime](../assets/pa-setup-procedure-34.png)

On the service management page, click the **Launch in** dropdown and select **IBM watsonx**.

![Step 35b — watsonx-ai-runtime service page with Launch in IBM watsonx button](../assets/pa-setup-procedure-35.png)

---

### Step 36 — Retrieve the Project ID from the watsonx homepage

The IBM watsonx console opens at `eu-de.dataplatform.cloud.ibm.com/wx/home`. The currently active project is shown at the top (e.g. **`<your-watsonx-project>`**).

If you do not yet have a project, create one by clicking the **Projects** tab in the horizontal tab bar, then **New project**.

To find the **Project ID**:

1. Click the **Projects** tab at the top of the watsonx home page.

![Step 36 — watsonx home page showing Projects tab and active project](../assets/pa-setup-procedure-36.png)

2. Open your project and click the **Manage** tab.
3. In the left sidebar under **Project**, click **General**.
4. The **Project ID** is shown in the Details section. Click the **copy to clipboard** icon next to it.

![Step 36b — Project Manage > General showing Project ID with copy button](../assets/pa-setup-procedure-37.png)

> In this example the Project ID is `<your-project-id>`. Use your own value.

---

### Step 37 — Generate an IBM Cloud API key

The `watsonx_api_key` is a personal IBM Cloud API key. Return to the IBM Cloud console.

In the top navigation bar, click **Manage → Access (IAM)**.

![Step 37 — IBM Cloud Manage menu open with Access (IAM) highlighted](../assets/pa-setup-procedure-38.png)

In the left sidebar, under **Manage identities**, click **API keys**, then click **Create +**.

Give the key a name (e.g. `watsonx-ai-runtime-key`), add an optional description, and click **Create**.

> ⚠️ The key value is displayed **only once** at creation time. Copy it immediately and store it securely.

![Step 37b — IAM API keys page with Create button and existing key](../assets/pa-setup-procedure-39.png)

---

### Step 38 — Compose and paste the watsonx.ai configuration JSON

Back in the Planning Analytics Integrations form, scroll down to the **Model provider — Configuration value** field.

Build the following JSON using the values you just collected:

```json
{
  "watsonx_api_url": "https://eu-de.ml.cloud.ibm.com",
  "watsonx_api_key": "<your IBM Cloud API key>",
  "watsonx_api_project_id": "<your-project-id>"
}
```

> The `watsonx_api_url` follows the pattern `https://<region>.ml.cloud.ibm.com`. Use `eu-de` for Frankfurt and `us-south` for Dallas.

Paste the completed JSON into the **Configuration value** field.

![Step 38 — PA form with watsonx.ai configuration JSON pasted in](../assets/pa-setup-procedure-40.png)

---

### Step 39 — Test and apply the configuration

With all three sections filled in, confirm their status:
- ✅ **Configuration value** — agent JSON (orchestrationID, hostURL, agentId, agentEnvironmentId, perspectives)
- ✅ **Embedded chat authorization key** — private RSA key (PEM format)
- ✅ **Model provider — Configuration value** — watsonx.ai JSON (API URL, API key, project ID)

Click **Test**. A green success toast should appear in the top-right corner:

> **✅ Connection test completed successfully.**

Then click **Apply** to save the configuration.

![Step 39 — Test successful — green toast notification visible](../assets/pa-setup-procedure-41.png)

> If the test fails, check the following:
> - The `orchestrationID`, `agentId`, and `agentEnvironmentId` exactly match the values from your Orchestrate snippet
> - The private key is complete, including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` header and footer lines
> - The `watsonx_api_key` and `watsonx_api_project_id` are correct, and the API key has access to the watsonx.ai Runtime service
> - The Orchestrate callback URL is registered as a Redirect URL in the Planning Analytics OAuth client (Step 5)

---

### Step 40 — Open the AI Chat in Planning Analytics

The integration is now live. Navigate to any Planning Analytics view included in your `perspectives` array (e.g. the home page, a dashboard, or the Administration page).

A **chat widget** appears on the right side of the screen. Click it to open the embedded chat. The **Planning Analytics Orchestrator** agent greets you and offers suggested prompts.

Send a test question — the agent responds using the 41 Planning Analytics tools connected via the MCP server.

![Step 40 — Planning Analytics with embedded chat widget open and agent responding](../assets/pa-setup-procedure-42.png)

> 🎉 **Congratulations! The AI Chat is now live within Planning Analytics.**
>
> Users can interact with the watsonx Orchestrate agent directly from within the Planning Analytics interface — asking questions about financial data, TM1 cubes, processes, and allocations — all powered by the 41 Planning Analytics tools exposed through the MCP server.

---

> ✅ **Section 3 complete. The full end-to-end integration is configured.**

---

## Summary — End-to-End Architecture

```mermaid
flowchart TD
    User(["Planning Analytics User"])

    subgraph PA["Planning Analytics Workspace"]
        Widget["Embedded Chat Widget\n(JWT signed with private key)"]
    end

    subgraph WXO["watsonx Orchestrate · eu-de"]
        OrchAgent["Planning Analytics\nOrchestrator Agent\n(live deployment)"]
    end

    subgraph MCP_SRV["Planning Analytics MCP Server"]
        MCPEndpoint["/api/v0/agentic-ai/ibm-pa-tools/mcp\n41 tools"]
    end

    subgraph TM1DB["Planning Analytics (TM1) Databases"]
        DB["your-instance environment"]
    end

    User --> Widget
    Widget -- "HTTPS + JWT\n(verified by public key in WxO)" --> OrchAgent
    OrchAgent -- "OAuth2 + MCP\n(Streamable HTTP)" --> MCPEndpoint
    MCPEndpoint -- "TM1 REST API" --> DB
```
