/**
 * Chat transport + wire→UI helpers for the chat feature.
 */
export { sendOmniMessage } from '../../lib/api/chat'
export type { ChatClientContext } from '../../lib/api/chat'
export { chatApiResponseToUi, parseWireChatPayload } from '../../lib/api/adapters'
