import { useState } from 'react'
import type { ChatRequestState, RuntimeMetadata } from '../../types'
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

export function RuntimeInspectorPanel({ metadata, sessionId, requestState }: RuntimeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState('summary')

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
          <RuntimeSummaryTab metadata={metadata} sessionId={sessionId} requestState={requestState} />
        ) : activeTab === 'governance' ? (
          <RuntimeGovernanceTab metadata={metadata} />
        ) : activeTab === 'tools' ? (
          <RuntimeToolsTab metadata={metadata} />
        ) : activeTab === 'provider' ? (
          <RuntimeProviderTab metadata={metadata} />
        ) : activeTab === 'memory' ? (
          <RuntimeMemoryTab metadata={metadata} />
        ) : activeTab === 'oil' ? (
          <RuntimeOilTab metadata={metadata} />
        ) : activeTab === 'logs' ? (
          <RuntimeLogsTab metadata={metadata} sessionId={sessionId} />
        ) : null}
      </div>
    </div>
  )
}
