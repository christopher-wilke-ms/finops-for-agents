# FinOps for Agents - A Hackathon Project

## Current Situation
AI agents enable organizations to automate processes, make knowledge more accessible, and empower employees to work more efficiently. At the same time, they introduce a new cost structure: in addition to infrastructure costs, usage-based expenses arise from token consumption, model calls, and agent executions.

## Challenge
Today, these costs are often captured centrally at the platform or agent level. The actual cost drivers — such as users, teams, applications, or business processes — often remain hidden. This makes it difficult to plan budgets, assess business value, and scale the productive use of AI agents in a controlled way.

## Solution Approach
FinOps for Agents builds on established and standardized FinOps practices. Existing models and approaches from the FinOps Foundation are extended and adapted to the specific requirements of agentic solutions. This includes agent-specific metrics such as token consumption, model usage, user interactions, and executions.

As a result, AI costs can be captured transparently and allocated to teams, applications, or business processes based on actual usage. The approach provides a compatible foundation for existing cloud FinOps processes, rather than creating an isolated cost model for AI agents.

## Business Value

Organizations gain a reliable basis for making informed decisions about the economic use of AI agents. They can identify which agents deliver the highest value, where optimization opportunities exist, and how AI investments can be managed more effectively. At the same time, the solution supports budgeting, showback, chargeback, reporting, and cost control.

By aligning with established FinOps standards, the approach can be integrated more easily into existing governance, controlling, and reporting structures.

## Target State

FinOps for Agents extends the model landscape of the FinOps Foundation by introducing a central interface for capturing agent-specific cost metrics. A realistic scenario is demonstrated using Microsoft Foundry as the agent runtime and Microsoft Teams and Microsoft 365 as entry points for user interactions. Additional components such as Azure API Management and a custom container app are addressed as part of the solution’s technical architecture.

Based on this data foundation, reports, dashboards, and automated analyses can be created. This enables organizations to operate agentic applications in a scalable, cost-effective, and financially sustainable way — built on established FinOps principles.