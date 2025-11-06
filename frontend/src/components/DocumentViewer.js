import React, { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import {
  Container,
  Box,
  Spinner,
  Alert
} from '@cloudscape-design/components';
import './DocumentViewer.css';

export default function DocumentViewer({
  markdown,
  loading,
  error,
  onTextSelect,
  onClearSelection,
  comments = []
}) {
  const viewerRef = useRef(null);
  const [, setSelection] = useState(null);
  const [highlightedRange, setHighlightedRange] = useState(null);
  const highlightSpanRef = useRef(null);

  // Memoize markdown components to prevent unnecessary re-renders
  const markdownComponents = useMemo(() => ({
    // Custom styling for markdown elements
    h1: ({ node, ...props }) => (
      // eslint-disable-next-line jsx-a11y/heading-has-content
      <h1 className="markdown-h1" {...props} />
    ),
    h2: ({ node, ...props }) => (
      // eslint-disable-next-line jsx-a11y/heading-has-content
      <h2 className="markdown-h2" {...props} />
    ),
    h3: ({ node, ...props }) => (
      // eslint-disable-next-line jsx-a11y/heading-has-content
      <h3 className="markdown-h3" {...props} />
    ),
    p: ({ node, ...props }) => (
      <p className="markdown-p" {...props} />
    ),
    ul: ({ node, ...props }) => (
      <ul className="markdown-ul" {...props} />
    ),
    ol: ({ node, ...props }) => (
      <ol className="markdown-ol" {...props} />
    ),
    code: ({ node, inline, className, children, ...props }) => {
      // Inline code: `code` (no className, inline=true or undefined)
      // Block code: ```code``` (has className with language-, inline=false)
      const isInline = inline !== false && !className;

      return isInline ? (
        <code className="markdown-inline-code" {...props}>
          {children}
        </code>
      ) : (
        <code className={`markdown-code-block ${className || ''}`} {...props}>
          {children}
        </code>
      );
    },
    pre: ({ node, children, ...props }) => (
      <pre className="markdown-code-block-wrapper" {...props}>
        {children}
      </pre>
    ),
    blockquote: ({ node, ...props }) => (
      <blockquote className="markdown-blockquote" {...props} />
    ),
    table: ({ node, ...props }) => (
      <div className="markdown-table-wrapper">
        <table className="markdown-table" {...props} />
      </div>
    ),
    img: ({ node, ...props }) => (
      <a
        href={props.src}
        target="_blank"
        rel="noopener noreferrer"
        className="markdown-img-link"
      >
        <img className="markdown-img" {...props} alt={props.alt || ''} />
      </a>
    ),
    a: ({ node, children, ...props }) => {
      // Extract domain from URL for display
      let displayText = children;
      try {
        // Remove brackets if present
        let urlText = String(children).replace(/^\[|\]$/g, '');
        const url = new URL(props.href || urlText);
        displayText = url.hostname.replace('www.', '');
      } catch (e) {
        // If URL parsing fails, just clean up brackets
        displayText = String(children).replace(/^\[|\]$/g, '');
      }

      return (
        <a
          className="markdown-link-chip"
          href={props.href}
          target="_blank"
          rel="noopener noreferrer"
          title={props.href}
        >
          <span className="link-chip-icon">🔗</span>
          <span className="link-chip-domain">{displayText}</span>
        </a>
      );
    }
  }), []);

  useEffect(() => {
    const handleSelection = () => {
      const selectedText = window.getSelection();
      const text = selectedText.toString().trim();

      if (text && viewerRef.current?.contains(selectedText.anchorNode)) {
        const range = selectedText.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const viewerRect = viewerRef.current.getBoundingClientRect();

        // Clone the range before it gets cleared
        const clonedRange = range.cloneRange();

        setSelection({
          text,
          position: {
            top: rect.top - viewerRect.top + rect.height,
            left: rect.left - viewerRect.left
          }
        });

        // Store the cloned range for persistent highlighting
        setHighlightedRange({
          startContainer: clonedRange.startContainer,
          startOffset: clonedRange.startOffset,
          endContainer: clonedRange.endContainer,
          endOffset: clonedRange.endOffset,
          text: text
        });

        if (onTextSelect) {
          onTextSelect({
            text,
            range: clonedRange,
            position: {
              top: rect.top - viewerRect.top + rect.height,
              left: rect.left - viewerRect.left
            }
          });
        }
      }
    };

    document.addEventListener('mouseup', handleSelection);
    return () => document.removeEventListener('mouseup', handleSelection);
  }, [onTextSelect]);

  // Apply highlighting to the stored range
  useEffect(() => {
    if (!highlightedRange || !viewerRef.current) return;

    // Remove previous highlights without normalizing (prevents font size flicker)
    const existingHighlights = viewerRef.current.querySelectorAll('.text-selection-highlight');
    existingHighlights.forEach(el => {
      const parent = el.parentNode;
      if (parent) {
        // Replace highlight span with its text content
        while (el.firstChild) {
          parent.insertBefore(el.firstChild, el);
        }
        parent.removeChild(el);
        // Don't normalize - it causes React re-render and font size changes
      }
    });

    // Apply highlight after a short delay to ensure DOM is ready
    const timeoutId = setTimeout(() => {
      if (!viewerRef.current || !highlightedRange) return;

      try {
        const range = document.createRange();
        range.setStart(highlightedRange.startContainer, highlightedRange.startOffset);
        range.setEnd(highlightedRange.endContainer, highlightedRange.endOffset);

        // Create highlight span
        const span = document.createElement('span');
        span.className = 'text-selection-highlight';
        span.setAttribute('data-highlight', 'true'); // Mark for easy identification

        // Try to surround contents
        try {
          range.surroundContents(span);
          highlightSpanRef.current = span;
          console.log('✅ Highlight applied successfully');
        } catch (surroundError) {
          // If surroundContents fails, use alternative method with DocumentFragment
          console.log('surroundContents failed, using alternative method');
          const fragment = range.extractContents();
          span.appendChild(fragment);
          range.insertNode(span);
          highlightSpanRef.current = span;
          console.log('✅ Highlight applied using fragment method');
        }
      } catch (e) {
        console.error('Could not apply highlight:', e);
      }
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [highlightedRange]);

  // Apply comment highlights (yellow background)
  useEffect(() => {
    if (!viewerRef.current || !markdown || comments.length === 0) return;

    // Wait for markdown to be rendered
    const timeoutId = setTimeout(() => {
      const viewer = viewerRef.current;
      if (!viewer) return;

      // Get list of already highlighted comment IDs
      const existingHighlightIds = new Set();
      viewer.querySelectorAll('.comment-highlight').forEach(el => {
        const commentId = el.getAttribute('data-comment-id');
        if (commentId) {
          existingHighlightIds.add(commentId);
        }
      });

      // Remove highlights for resolved comments
      viewer.querySelectorAll('.comment-highlight').forEach(el => {
        const commentId = el.getAttribute('data-comment-id');
        const comment = comments.find(c => c.id === commentId);
        if (!comment || comment.status === 'resolved') {
          const parent = el.parentNode;
          if (parent) {
            while (el.firstChild) {
              parent.insertBefore(el.firstChild, el);
            }
            parent.removeChild(el);
          }
        }
      });

      // Add highlights only for new pending comments
      comments.forEach(comment => {
        if (!comment.selectedText || comment.status === 'resolved') return;

        // Skip if already highlighted
        if (existingHighlightIds.has(comment.id)) {
          return;
        }

        try {
          const walker = document.createTreeWalker(
            viewer,
            NodeFilter.SHOW_TEXT,
            null,
            false
          );

          let node;
          while ((node = walker.nextNode())) {
            // Skip if this text node is already inside a comment-highlight
            let parent = node.parentNode;
            let insideHighlight = false;
            while (parent && parent !== viewer) {
              if (parent.classList && parent.classList.contains('comment-highlight')) {
                insideHighlight = true;
                break;
              }
              parent = parent.parentNode;
            }
            if (insideHighlight) continue;

            const text = node.textContent;
            const index = text.indexOf(comment.selectedText);

            if (index >= 0) {
              const range = document.createRange();
              range.setStart(node, index);
              range.setEnd(node, index + comment.selectedText.length);

              const span = document.createElement('span');
              span.className = 'comment-highlight';
              span.setAttribute('data-comment-id', comment.id);
              span.title = comment.comment;

              // Add click handler to scroll to comment
              span.onclick = (e) => {
                e.preventDefault();
                const commentId = comment.id;
                const commentCard = document.querySelector(`[data-comment-card-id="${commentId}"]`);
                if (commentCard) {
                  commentCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                  // Add brief highlight effect
                  commentCard.style.transition = 'background-color 0.3s';
                  commentCard.style.backgroundColor = '#e6f2ff';
                  setTimeout(() => {
                    commentCard.style.backgroundColor = '';
                  }, 1000);
                }
              };

              try {
                range.surroundContents(span);
                break; // Found and highlighted, move to next comment
              } catch (e) {
                console.warn('Could not highlight text:', e);
              }
            }
          }
        } catch (e) {
          console.error('Error applying comment highlight:', e);
        }
      });
    }, 200);

    return () => clearTimeout(timeoutId);
  }, [markdown, comments]);

  // Clear selection function exposed via onClearSelection callback
  useEffect(() => {
    const clearSelection = () => {
      // Clear the browser selection
      window.getSelection().removeAllRanges();

      // Remove highlight span without normalizing
      if (highlightSpanRef.current && viewerRef.current) {
        const parent = highlightSpanRef.current.parentNode;
        if (parent) {
          // Move children out of span before removing
          while (highlightSpanRef.current.firstChild) {
            parent.insertBefore(highlightSpanRef.current.firstChild, highlightSpanRef.current);
          }
          parent.removeChild(highlightSpanRef.current);
          // Don't normalize - it causes React re-render and font size changes
        }
        highlightSpanRef.current = null;
      }

      // Clear state
      setHighlightedRange(null);
      setSelection(null);
    };

    // Expose clear function to parent
    if (onClearSelection) {
      onClearSelection.current = clearSelection;
    }
  }, [onClearSelection]);

  if (loading) {
    return (
      <Container>
        <Box textAlign="center" padding="xxl">
          <Spinner size="large" />
          <Box variant="p" padding={{ top: 's' }}>
            Loading document...
          </Box>
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container>
        <Alert type="error" header="Failed to load document">
          {error}
        </Alert>
      </Container>
    );
  }

  if (!markdown) {
    return (
      <Container>
        <Alert type="info" header="No document available">
          The research document is not yet available.
        </Alert>
      </Container>
    );
  }

  return (
    <div className="document-viewer-wrapper">
      <Container>
        <div
          ref={viewerRef}
          className="document-viewer-content"
          suppressContentEditableWarning={true}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw, rehypeSanitize]}
            components={markdownComponents}
          >
            {markdown}
          </ReactMarkdown>
        </div>
      </Container>
    </div>
  );
}
