import { useState } from 'react'
import type { ChatRequestState } from '../../types'
import type { RuntimeInspectorData } from '../../lib/runtimeTypes'
import { buildRuntimeInspectorLinks } from '../../lib/runtimeLinks'
import { OmniTabs } from '../ui/OmniTabs'
import { RuntimeSummaryTab } from './RuntimeSummaryTab'
import { RuntimeGovernanceTab } from './RuntimeGovernanceTab'
import { RuntimeToolsTab } from './RuntimeToolsTab'
import { RuntimeProviderTab } from './RuntimeProviderTab'
import { RuntimeMemoryTab } from './RuntimeMemoryTab'
import { RuntimeOilTab } from './RuntimeOilTab'
import { RuntimeAutonomyTab } from './RuntimeAutonomyTab'
import { RuntimeLogsTab } from './RuntimeLogsTab'

type RuntimeInspectorPanelProps = {
  data: RuntimeInspectorData | null
  requestState: ChatRequestState
}

const TABS = [
  { id: 'summary', label: 'Summary' },
  { id: 'governance', label: 'Governance' },
  { id: 'autonomy', label: 'Autonomia' },
  { id: 'tools', label: 'Tools' },
  { id: 'provider', label: 'Provider' },
  { id: 'memory', label: 'Memory' },
  { id: 'oil', label: 'OIL' },
  { id: 'logs', label: 'Logs' },
]

export function RuntimeInspectorPanel({ data, requestState }: RuntimeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState('summary')
  const links = buildRuntimeInspectorLinks(data)

  return (
    <div className="flex h-full flex-col">
      <OmniTabs
        tabs={TABS}
        activeTab={activeTab}
        onSelect={setActiveTab}
        className="mb-3"
      />
      <div className="flex-1 overflow-y-auto pr-1">
        {activeTab === 'summary' ? (
          <RuntimeSummaryTab
            data={data?.summary ?? null}
            provider={data?.provider ?? null}
            requestState={requestState}
            observabilityHref={links.observability}
          />
        ) : activeTab === 'governance' ? (
          <RuntimeGovernanceTab
            data={data?.governance ?? null}
            governanceHref={links.governance}
          />
        ) : activeTab === 'tools' ? (
          <RuntimeToolsTab data={data?.tools ?? []} executionHref={links.tool} />
        ) : activeTab === 'provider' ? (
          <RuntimeProviderTab
            data={data?.providers ?? []}
            autoRouting={data?.provider_auto_routing ?? null}
            providerHref={links.provider}
          />
        ) : activeTab === 'memory' ? (
          <RuntimeMemoryTab data={data?.memory ?? null} />
        ) : activeTab === 'autonomy' ? (
          <RuntimeAutonomyTab data={data?.autonomy ?? null} stats={data?.autonomy_stats ?? null} />
        ) : activeTab === 'oil' ? (
          <RuntimeOilTab data={data?.oil ?? null} />
        ) : activeTab === 'logs' ? (
          <RuntimeLogsTab data={data?.logs ?? null} logsHref={links.logs} />
        ) : null}
      </div>
    </div>
  )
}
