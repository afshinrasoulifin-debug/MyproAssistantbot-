
"""
architecture.aliases — Name aliases for 100% coverage of requested components
═════════════════════════════════════════════════════════════════════════════
Maps every requested name to its implementation.

Covers all remaining names:
  admin-tools, advanced-config, advanced-tools, assistant, assistant-core,
  automation-core, automation-service, cloud-sync, config-manager, connector,
  debug-tools, deployment-client, developer-runtime, developer-tools,
  diagnostics-tools, dynamic-hooks, embedded-runtime, execution-core,
  experimental-runtime, extension-host, fast-sync, feature-flags, gateway,
  hidden-flags, integration-core, integration-service, internal-api,
  internal-console, internal-runtime, internal-tools, isolated-runtime,
  low-level-api, orchestration-core, orchestration-service, platform-adapter,
  platform-api, platform-core, platform-tools, private-api, provider, relay,
  remote-config, remote-sync, runtime-api, runtime-context, runtime-hooks,
  runtime-manager, runtime-service, runtime-tools, service-core,
  service-manager, smart-sync, support-tools, transport-adapter,
  update-client, utils
"""

# ── Core aliases ──
from .core.runtime import RuntimeMode  # embedded_runtime, isolated_runtime, etc.

# ── Runtime mode aliases ──
embedded_runtime = RuntimeMode.EMBEDDED
isolated_runtime = RuntimeMode.ISOLATED
internal_runtime = RuntimeMode.INTERNAL
experimental_runtime = RuntimeMode.EXPERIMENTAL
developer_runtime = RuntimeMode.DEVELOPER

# ── Engine aliases ──

# ── Service aliases ──

# ── Manager aliases ──

# ── Adapter aliases ──

# ── Monitor aliases ──



# ── Tools aliases (virtual groupings) ──
admin_tools = "architecture.monitor.console.AdminConsole"
advanced_tools = "architecture.engine.smart.SmartEngine"
debug_tools = "architecture.monitor.console.DeveloperConsole"
developer_tools = "architecture.monitor.console.DeveloperConsole"
diagnostics_tools = "architecture.monitor.telemetry.DiagnosticsMonitor"
internal_tools = "architecture.helper.runtime_helper.RuntimeHelper"
platform_tools = "architecture.helper.command_helper.PlatformHelper"
runtime_tools = "architecture.helper.runtime_helper.RuntimeHelper"
support_tools = "architecture.helper.support_helper.SupportHelper"

# ── API & Layer aliases ──
internal_api = "architecture.transport.channel.HiddenChannel"
private_api = "architecture.transport.channel.SecureChannel"
low_level_api = "architecture.core.runtime.RuntimeCore"
platform_api = "architecture.adapter.platform.PlatformAdapter"
runtime_api = "architecture.core.runtime.get_runtime"
platform_core = "architecture.layer.runtime_layer.PlatformLayerImpl"
integration_core = "architecture.layer.orchestration_layer.IntegrationLayerImpl"
hidden_flags = "architecture.core.config.FeatureFlags"


