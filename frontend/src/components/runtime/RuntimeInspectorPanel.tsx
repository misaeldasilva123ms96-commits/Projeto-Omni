import { useMemo, useState } from 'react'
import type { ChatRequestState, RuntimeMetadata } from '../../types'
import { normalizeRuntimeInspectorData } from '../../lib/runtimeTypes'
import { OmniTabs } from '../ui/OmniTabs'
import { RuntimeSummaryTab } from './RuntimeSummaryTab'
import { RuntimeGovernanceTab } from './RuntimeGovernanceTab'
import { RuntimeToolsTab } from './RuntimeToolsTab'
import { RuntimeProviderTab } from './RuntimeProviderTab'
import { RuntimeMemoryTab } from './RuntimeMemoryTab'
import { RuntimeOilTab } from './RuntimeOilTab'
import { RuntimeLogsTab } from './RuntimeLogsTab'

type RuntimeInspectorPanelProps = {
  metadata: RuntimeMetadata | null
  sessionId: string
  requestState: ChatRequestState
}

const TABS = [
  { id: 'summary', label: 'Summary' },
  { id: 'governance', label: 'Governance' },
  { id: 'tools', label: 'Tools' },
  { id: 'provider', label: 'Provider' },
  { id: 'memory', label: 'Memory' },
  { id: 'oil', label: 'OIL' },
  { id: 'logs', label: 'Logs' },
]

export function RuntimeInspectorPanel({ metadata, requestState }: RuntimeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState('summary')
  const data = useMemo(() => normalizeRuntimeInspectorData(metadata), [metadata])

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
            data={data.summary}
            provider={data.provider}
            requestState={requestState}
            hasMetadata={Boolean(metadata)}
          />
        ) : activeTab === 'governance' ? (
          <RuntimeGovernanceTab data={data.governance} />
        ) : activeTab === 'tools' ? (
          <RuntimeToolsTab data={data.tools} />
        ) : activeTab === 'provider' ? (
          <RuntimeProviderTab data={data.providers} />
        ) : activeTab === 'memory' ? (
          <RuntimeMemoryTab data={data.memory} />
        ) : activeTab === 'oil' ? (
          <RuntimeOilTab data={data.oil} />
        ) : activeTab === 'logs' ? (
          <RuntimeLogsTab data={data.logs} />
        ) : null}
      </div>
    </div>
  )
}
