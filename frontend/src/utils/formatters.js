/**
 * Utility functions for formatting data
 */

import { formatModelName as getModelLabel } from '../config/modelRegistry';

/**
 * Format date/time in local timezone
 */
export function formatDate(timestamp) {
  if (!timestamp) return '-';

  const date = new Date(timestamp);

  // Ensure valid date
  if (isNaN(date.getTime())) return '-';

  // Get local timezone abbreviation
  const timeZoneAbbr = date.toLocaleTimeString('en-US', { timeZoneName: 'short' }).split(' ').pop();

  // Format with explicit local timezone
  const formatted = date.toLocaleString(undefined, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });

  return `${formatted} ${timeZoneAbbr}`;
}

/**
 * Format elapsed time
 * @param {number} elapsedSeconds - Elapsed time in seconds (not a timestamp!)
 */
export function formatElapsedTime(elapsedSeconds) {
  if (!elapsedSeconds || elapsedSeconds < 0) return '0s';

  const hours = Math.floor(elapsedSeconds / 3600);
  const minutes = Math.floor((elapsedSeconds % 3600) / 60);
  const seconds = Math.floor(elapsedSeconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  } else if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

/**
 * Format file size
 */
export function formatFileSize(bytes) {
  if (!bytes) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

/**
 * Truncate text
 */
export function truncateText(text, maxLength = 100) {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Format research status
 */
export function getStatusBadgeType(status) {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
    case 'in_progress':
      return 'in-progress';
    case 'failed':
    case 'error':
      return 'error';
    case 'pending':
      return 'pending';
    default:
      return 'info';
  }
}

/**
 * Format research type label
 */
export function formatResearchType(type) {
  const labels = {
    'basic_web': 'Basic Web',
    'advanced_web': 'Advanced Web',
    'academic': 'Academic',
    'financial': 'Financial',
    'comprehensive': 'Comprehensive'
  };
  return labels[type] || type;
}

/**
 * Format research depth label
 */
export function formatResearchDepth(depth) {
  const labels = {
    'quick': 'Quick',
    'balanced': 'Balanced',
    'deep': 'Deep'
  };
  return labels[depth] || depth;
}

/**
 * Format model name (using centralized model registry)
 */
export function formatModelName(model) {
  return getModelLabel(model);
}
