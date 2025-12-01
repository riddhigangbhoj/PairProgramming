# Monaco Editor Integration Design

**Date:** 2025-12-01
**Status:** Approved
**Approach:** Hybrid (Monaco APIs + WebSocket sync)

## Overview

Upgrade the pair programming app from a basic textarea to a full-featured Monaco Editor (VS Code editor) with:
- AI-powered inline autocomplete (Copilot-style)
- Multi-user cursor tracking and selections
- Real-time collaborative editing
- Professional code editing experience

## 1. Monaco Editor Basic Setup

### Component Architecture
Refactor `CodeEditor.tsx` to use `@monaco-editor/react` instead of `<textarea>`.

### Configuration
```typescript
<Editor
  height="600px"
  language={language}
  value={code}
  onChange={handleEditorChange}
  options={{
    minimap: { enabled: true },
    fontSize: 14,
    lineNumbers: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    quickSuggestions: false,  // Disable built-in autocomplete
    suggestOnTriggerCharacters: false,
    tabSize: 2,
    insertSpaces: true,
  }}
  onMount={handleEditorDidMount}
/>
```

### State Management
- Maintain `editorRef` for imperative API access
- Store Monaco instance reference for registering providers
- Track editor version for change detection

## 2. AI Inline Autocomplete (Copilot-Style)

### InlineCompletionItemProvider API
Register custom provider using Monaco's built-in API for ghost text suggestions.

```typescript
monaco.languages.registerInlineCompletionsProvider(language, {
  provideInlineCompletions: async (model, position, context, token) => {
    const code = model.getValue();
    const offset = model.getOffsetAt(position);

    const suggestions = await fetchAISuggestions(code, offset, language);

    return {
      items: suggestions.map(text => ({
        insertText: text,
        range: new monaco.Range(
          position.lineNumber,
          position.column,
          position.lineNumber,
          position.column
        )
      }))
    };
  },
  freeInlineCompletions: () => {}
});
```

### Triggering Strategy
- **Debounce**: 500ms after typing stops
- **Smart triggers**: Only on meaningful changes (not cursor movement)
- **Cancel in-flight**: Abort previous requests when new ones start
- **Rate limit**: Max 1 request per second

### Visual Feedback
- Loading indicator in status bar during fetch
- Display confidence score if >70%
- Support cycling through multiple suggestions

## 3. Multi-User Cursor Tracking

### Decorations API
Use Monaco's decorations to show remote user cursors and selections.

```typescript
const userDecorations = new Map<string, string[]>();

function updateRemoteCursor(
  userId: string,
  position: {line: number, column: number},
  userName: string
) {
  const color = getUserColor(userId);

  const decorations = editor.deltaDecorations(
    userDecorations.get(userId) || [],
    [{
      range: new monaco.Range(
        position.line, position.column,
        position.line, position.column
      ),
      options: {
        className: `remote-cursor-${userId}`,
        beforeContentClassName: `cursor-line`,
        after: {
          content: userName,
          inlineClassName: `cursor-label-${userId}`
        }
      }
    }]
  );

  userDecorations.set(userId, decorations);
}
```

### WebSocket Protocol Enhancement
```typescript
// Client → Server: Cursor update
{
  type: 'cursor_update',
  data: {
    user_id: 'user-123',
    user_name: 'Alice',
    position: { line: 10, column: 5 },
    selection: {
      startLine: 10, startColumn: 5,
      endLine: 10, endColumn: 15
    }
  }
}

// Server → Clients: Broadcast cursor
// Same format, broadcast to all except sender
```

### Styling
- Unique color per user from predefined palette
- Animated pulse effect on cursor
- Semi-transparent selection backgrounds
- Floating name labels above cursors

## 4. Real-time Code Synchronization

### Strategy: Operational Transform (Simplified)
Send change events instead of full code to avoid race conditions.

```typescript
// Change event structure
{
  type: 'code_change',
  data: {
    changes: [{
      range: {
        startLine: 2, startColumn: 5,
        endLine: 2, endColumn: 5
      },
      text: 'hello',
      rangeLength: 0  // 0 = insert, >0 = replace/delete
    }],
    versionId: 42
  }
}
```

### Applying Remote Changes
Use `executeEdits()` to avoid triggering local `onChange`:

```typescript
editor.executeEdits('remote-user', [{
  range: remoteChange.range,
  text: remoteChange.text,
  forceMoveMarkers: true
}]);
```

### Cursor Position Adjustment
Auto-adjust cursor positions when remote edits occur:
- Track line/column changes from remote edits
- Shift cursors that come after the edit position
- Preserve relative cursor positions

### Conflict Resolution
**Last-write-wins** approach (simple, suitable for pair programming).

### Backend Changes
WebSocket handler broadcasts changes to all users except sender, preserving metadata.

## 5. Error Handling & Edge Cases

### WebSocket Disconnection
- Show "Connection lost. Reconnecting..." banner
- Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- On reconnect: fetch latest code from REST API
- Make editor read-only during disconnection

### Out-of-Sync State
- Version mismatch detection
- "Changes pending sync" warning if needed
- Manual refresh button to reload room state
- Periodic ping/pong health checks (every 30s)

### AI Autocomplete Resilience
- 500ms debounce after typing stops
- Cancel pending requests on new input
- Max 1 request per second
- Silent failure (don't break editing if AI fails)
- Loading indicator in status bar

### Performance Optimization
- Disable decorations for files >10,000 lines
- Throttle cursor updates to max every 100ms
- Cleanup decorations when users leave
- Lazy load Monaco with fallback

### Monaco Loading Fallback
- Show loading spinner during Monaco CDN load
- Fallback to textarea if Monaco fails after 10s
- React error boundary for Monaco crashes

### Edge Cases
- Empty room (first user with no code)
- User leaves during edit (immediate cleanup)
- Rapid language changes (debounce selector)

## Implementation Plan

### Phase 1: Monaco Basic Integration
1. Replace textarea with Monaco Editor
2. Configure options and styling
3. Wire up onChange handler
4. Test basic editing works

### Phase 2: AI Inline Autocomplete
1. Register InlineCompletionItemProvider
2. Implement debounced API calls
3. Add loading indicators
4. Test suggestions appear and accept with Tab

### Phase 3: Multi-User Cursors
1. Implement decoration management
2. Add cursor update WebSocket messages
3. Assign colors to users
4. Add CSS styling for cursors
5. Test with multiple browser tabs

### Phase 4: Real-Time Sync
1. Change from full-code sync to change-events
2. Implement executeEdits for remote changes
3. Add cursor position adjustment logic
4. Update WebSocket backend handler
5. Test concurrent editing

### Phase 5: Error Handling
1. Add WebSocket reconnection logic
2. Implement read-only mode during disconnect
3. Add rate limiting to AI calls
4. Add Monaco loading fallback
5. Test edge cases

## Success Criteria

- ✅ Monaco Editor loads and renders correctly
- ✅ AI suggestions appear as grey text, accept with Tab
- ✅ Remote user cursors visible with names and colors
- ✅ Multiple users can edit simultaneously without conflicts
- ✅ Reconnection works after disconnect
- ✅ Graceful degradation if AI/Monaco fails
- ✅ Performance acceptable for files up to 1000 lines

## Non-Goals (Future Enhancements)

- CRDT-based sync (Yjs) - overkill for current use case
- Conflict resolution UI - last-write-wins is sufficient
- Advanced OT with transform functions - simplified approach works
- Video/audio chat integration - separate feature
- Code execution - separate feature

## Technology Choices

- **@monaco-editor/react** v4.6.0 (already installed)
- **Monaco Editor** (VS Code engine)
- **WebSocket** (existing infrastructure)
- **React** 18.2+ with TypeScript
- **Debouncing** via custom hook or lodash

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Monaco CDN fails to load | Fallback to textarea, show error message |
| WebSocket drops during edit | Auto-reconnect + fetch latest state from API |
| Concurrent edit conflicts | Last-write-wins + visual cursor indicators |
| AI API rate limits hit | Debounce + cancel pending + max 1/sec |
| Large file performance | Disable decorations/autocomplete for >10k lines |

## Timeline Estimate

- Implementation: 30-45 minutes
- Testing: 10-15 minutes
- Total: ~1 hour

---

**Approved for implementation on 2025-12-01**
