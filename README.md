# Platform Outage Checker Bot

## Overview
The **Platform Outage Checker Bot** is a Python-based web application that monitors the health status of multiple services (Azure, Azure DevOps, GitHub, O365, ReTool, Salesforce, Slack, and Snowflake) and integrates with Slack for real-time notifications. 

This bot enables users to:
- Monitor services for outages.
- Automatically log and track service events.
- Create Azure DevOps tickets directly from Slack.
- Resolve and manage service events.

The app is designed to run on **Azure App Service** and is built with **Flask** and **Gunicorn** as the WSGI server. The deployment to Azure Web App ensures that Gunicorn listens on port 8000. It includes several service checkers for each platform and communicates through Slack via slash commands for manual overrides and interactions.

## Key Features
- Monitors multiple services' status.
- Integrates with Slack to notify users of ongoing outages or resolved issues.
- Logs service events in **Azure Table Storage**.
- Enables manual interventions through Slack commands to create tickets, force resolve events, etc.
- Tracks service events to avoid repetitive notifications.

## Process Flow
1. Service Checking:
- Each service has a checker (e.g., AzureServiceChecker.py, SlackServiceChecker.py) that runs at intervals (defined in tasks.py using APScheduler).
- If an outage or event is detected, it logs the event into Azure Table Storage via event_tracker.py.

2. Slack Integration:
- The app integrates with Slack using slash commands (e.g., /botstatus, /create_ticket).
- Events are posted in Slack channels when a service goes down or is resolved.
- Users can interact with incidents (e.g., creating tickets) through buttons in Slack.

3. Event Logging:
- Tracked Events are stored in an Azure Table (EVENT_TABLE_NAME).
- Events can be manually marked as resolved or automatically tracked until they are resolved by the service checker.
- Resolved events are moved to a separate Resolved Events table to avoid repeated notifications.

## Ticket Creation in Azure DevOps:
When a service event that affects us is posted, the bot can create an Azure DevOps work item through a button or slash command.
The ticket is logged along with the event details, including platform, event name, status, and description.

## Manual Commands via Slack:
The bot offers several manual overrides through Slack commands:
| Command                    | Description |
|------------------------------------|-------------|
|/BotStatus | Gives the current status of the web app (Healthy, Unhealthy, etc.).|
|/TestModeOn |	Turns on test mode for all service checkers.|
|/TestModeOff |	Turns off test mode for all service checkers.|
|/ManualCheck {Platform} |	Runs the service checker for the specified platform manually.|
|/CreateTicket {Internal ID} |	Creates an ADO ticket for the event with the given internal ID.|
|/ForceResolve {Internal ID} |	Forcefully moves the event with the matching internal ID to the resolved table.|
|/ListEvents |	Lists all currently tracked events.|

## Project Structure
```
platform-outage-checker/
├── .vscode/
├── antenv/
├── ServiceCheckers/
│   ├── ADOServiceChecker.py
│   ├── AzureServiceChecker.py
│   ├── GithubServiceChecker.py
│   ├── O365ServiceChecker.py
│   ├── ReToolServiceChecker.py
│   ├── SalesforceServiceChecker.py
│   ├── SnowflakeServiceChecker.py
│   └── SlackServiceChecker.py
├── service_event_checker/ 
│   ├── __init__.py
│   ├── routes.py
│   ├── tasks.py
│   ├── utils.py
│   ├── config.py
│   ├── event_tracker.py
│   └── slack_interaction.py
├── .deployment
├── .gitignore
├── app.py
├── config.json
├── requirements.txt
├── runtime.txt
```
## Architecture
- Azure Web App Resource: https://portal.azure.com/?feature.msaljs=false#@affinaquest.com/resource/subscriptions/6208a8ff-9ec7-4320-b14a-f89dabb55bf1/resourcegroups/rg-outage-bot/providers/Microsoft.Web/sites/app-i-outage-bot/appServices
    - Domain: app-i-outage-bot-gpbeeth4huazdhec.eastus2-01.azurewebsites.net
    - SCM: app-i-outage-bot-gpbeeth4huazdhec.scm.eastus2-01.azurewebsites.net
    - OS: Linux
    - Runtime: Python-3.12
    - SKU: B1

- Github: https://github.com/AbbiGrey/Platform-Outage-Checker

- Azure Storage: https://portal.azure.com/?feature.msaljs=false#@affinaquest.com/resource/subscriptions/6208a8ff-9ec7-4320-b14a-f89dabb55bf1/resourceGroups/rg-outage-bot/providers/Microsoft.Storage/storageAccounts/saioutagebot/overview
    - Active Event Table: EventTickets
    - Resolved Event Table: ResolvedEvents
    
- App Registration: https://portal.azure.com/?feature.msaljs=false#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/Overview/appId/461c3430-9588-42e7-b9c5-07b6a3fd8565/isMSAApp~/false
    - Client ID: 461c3430-9588-42e7-b9c5-07b6a3fd8565
    - Object ID (Enterprise App): 77d34da8-0a2b-43f7-af99-f4af16c47879

## Endpoints
- ADO: https://status.dev.azure.com/_apis/status/health?geographies=US&api-version=7.2-preview.1
- Azure: https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.ResourceHealth/events?api-version=2024-02-01
- Github: https://www.githubstatus.com/api/v2/incidents/unresolved.json
- O365: https://graph.microsoft.com/v1.0/admin/serviceAnnouncement/issues
- ReTool: https://status.retool.com/history.rss
- Salesforce: https://status.salesforce.com/api/incidents/active
- Slack: https://slack-status.com/api/v2.0.0/current
- Snowflake: https://status.snowflake.com/api/v2/incidents.json

## Environment Variables Documentation

The following environment variables are set in the Azure Web App:

| Variable Name                     | Description |
|------------------------------------|-------------|
| `ADO_ORG_URL`                      | The URL of the Azure DevOps organization. Used for integrating with Azure DevOps to create and manage tickets. |
| `ADO_PAT`                          | Personal Access Token (PAT) for authenticating to Azure DevOps. Used for API calls to manage work items and projects. |
| `ADO_PAT_BASE64`                   | Base64-encoded Personal Access Token for Azure DevOps. This is used in HTTP requests that require authentication. |
| `ADO_PROJECT`                      | The Azure DevOps project name where work items (tickets) are created for incidents. |
| `AZURE_CLIENT_ID`                  | Client ID for App Registration "External Platform Outage Bot". This is required to authenticate API calls to Azure services. |
| `AZURE_CLIENT_SECRET`              | Client secret for App Registration "External Platform Outage Bot". Used alongside the client ID for secure API access. |
| `AZURE_DEVOPS_ORG`                 | The Azure DevOps organization name used in API requests. |
| `AZURE_DEVOPS_PAT`                 | Same as ADO_PAT, used due to same enviroment variable value being needed but with different names for different uses. |
| `AZURE_STORAGE_CONNECTION_STRING`  | Connection string for Azure Storage, where the bot stores event tracking data, including active and resolved events. |
| `AZURE_TABLE_NAME`                 | The Azure Storage Table name where active service event tickets are stored. |
| `AZURE_TENANT_ID`                  | Tenant ID for Azure tenant that owns the Azure services. |
| `CLIENT_ID`                        | Same as `AZURE_CLIENT_ID`, used due to same enviroment variable value being needed but with different names for different uses. |
| `CLIENT_SECRET`                    | Same as `AZURE_CLIENT_SECRET`, used due to same enviroment variable value being needed but with different names for different uses. |
| `ESCALATE_EMAILS`                  | A list of email addresses that receive escalations. Used for sending out notifications for high-priority incidents. |
| `RESOLVED_EVENTS_TABLE`            | The Azure Storage Table name where resolved service events are stored. This prevents duplicate notifications for already resolved issues. |
| `SCM_DO_BUILD_DURING_DEPLOYMENT`   | A setting that triggers a build during the deployment process. |
| `SENDGRID_API_KEY`                 | API key for SendGrid, a service used to send email notifications. This key allows the bot to send incident-related emails. |
| `SENDGRID_SENDER_EMAIL`            | The email address used as the sender for incident notifications sent via SendGrid. |
| `SLACK_BOT_TOKEN`                  | The OAuth token for the Slack bot. Used to authenticate the bot and allow it to send messages, interact with users, and handle Slack commands. |
| `SLACK_VERIFICATION_TOKEN`         | Token used to verify the authenticity of Slack requests, ensuring that commands and interactions are coming from Slack. |
| `TENANT_ID`                        | Same as `AZURE_TENANT_ID`, used due to same enviroment variable value being needed but with different names for different uses. |
| `USER_OBJECT_ID`                   | The Azure Active Directory object ID for a specific user or service principal, used in authentication processes. |
| `WEBSITE_HTTPLOGGING_RETENTION_DAYS`| The number of days HTTP logs will be retained in the Azure Web App for debugging purposes. |

### Additional Notes:

- **Azure Storage**: The application logs events in Azure Table Storage using the `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_TABLE_NAME`, and `RESOLVED_EVENTS_TABLE`. These tables store the status of service events to prevent redundant notifications.
  
- **Azure DevOps Integration**: The environment variables prefixed with `ADO_` and `AZURE_DEVOPS_` are crucial for integrating with Azure DevOps. They allow the bot to create work items (tickets) in response to service incidents.

- **Slack Integration**: The `SLACK_BOT_TOKEN` and `SLACK_VERIFICATION_TOKEN` are required for the bot to operate in Slack, responding to commands like `/BotStatus` and handling interactive elements like buttons.

- **SendGrid Integration**: The `SENDGRID_API_KEY` and `SENDGRID_SENDER_EMAIL` are used for sending email notifications about outages or escalations to the addresses specified in `ESCALATE_EMAILS`.

