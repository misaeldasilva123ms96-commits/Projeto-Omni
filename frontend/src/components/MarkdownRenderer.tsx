import type { ReactNode } from 'react'

type Block =
  | { type: 'code'; code: string; language?: string }
  | { type: 'heading'; depth: 1 | 2 | 3; text: string }
  | { items: string[]; ordered: boolean; type: 'list' }
  | { text: string; type: 'paragraph' }

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(`[^`]+`)/g)
  return parts.map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return <code key={`${part}-${index}`}>{part.slice(1, -1)}</code>
    }
    return <span key={`${part}-${index}`}>{part}</span>
  })
}

function parseMarkdown(content: string): Block[] {
  const normalized = content.replace(/\r\n/g, '\n')
  const lines = normalized.split('\n')
  const blocks: Block[] = []
  let index = 0

  while (index < lines.length) {
    const line = lines[index]
    const trimmed = line.trim()

    if (!trimmed) {
      index += 1
      continue
    }

    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim() || undefined
      const codeLines: string[] = []
      index += 1

      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index])
        index += 1
      }

      if (index < lines.length) {
        index += 1
      }

      blocks.push({
        type: 'code',
        code: codeLines.join('\n'),
        language,
      })
      continue
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/)
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        depth: headingMatch[1].length as 1 | 2 | 3,
        text: headingMatch[2],
      })
      index += 1
      continue
    }

    const listMatch = trimmed.match(/^([-*+]|\d+\.)\s+(.+)$/)
    if (listMatch) {
      const ordered = /\d+\./.test(listMatch[1])
      const items: string[] = []

      while (index < lines.length) {
        const current = lines[index].trim()
        const currentMatch = current.match(/^([-*+]|\d+\.)\s+(.+)$/)
        if (!currentMatch) {
          break
        }
        items.push(currentMatch[2])
        index += 1
      }

      blocks.push({ type: 'list', ordered, items })
      continue
    }

    const paragraphLines: string[] = []
    while (index < lines.length) {
      const current = lines[index]
      const currentTrimmed = current.trim()
      if (!currentTrimmed || currentTrimmed.startsWith('```') || /^(#{1,3})\s+/.test(currentTrimmed) || /^([-*+]|\d+\.)\s+/.test(currentTrimmed)) {
        break
      }
      paragraphLines.push(currentTrimmed)
      index += 1
    }

    blocks.push({
      type: 'paragraph',
      text: paragraphLines.join(' '),
    })
  }

  return blocks
}

export function MarkdownRenderer({ content }: { content: string }) {
  const blocks = parseMarkdown(content)

  return (
    <div className="markdown-content">
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          if (block.depth === 1) {
            return <h1 key={index}>{renderInline(block.text)}</h1>
          }
          if (block.depth === 2) {
            return <h2 key={index}>{renderInline(block.text)}</h2>
          }
          return <h3 key={index}>{renderInline(block.text)}</h3>
        }

        if (block.type === 'code') {
          return (
            <pre key={index} className="code-block">
              {block.language ? <span className="code-language">{block.language}</span> : null}
              <code>{block.code}</code>
            </pre>
          )
        }

        if (block.type === 'list') {
          const ListTag = block.ordered ? 'ol' : 'ul'
          return (
            <ListTag key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={`${item}-${itemIndex}`}>{renderInline(item)}</li>
              ))}
            </ListTag>
          )
        }

        return <p key={index}>{renderInline(block.text)}</p>
      })}
    </div>
  )
}
