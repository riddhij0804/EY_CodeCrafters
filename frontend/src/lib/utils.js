import { clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}
/**
 * Resolve image URLs to proper URLs
 * Prioritizes Supabase full URLs (https://...) and uses them directly
 * Falls back to local backend for relative paths
 */
export function resolveImageUrl(imagePath) {
  if (!imagePath) return null;
  
  // If it's already a full HTTPS URL (likely from Supabase), use as-is
  if (imagePath.startsWith('https://')) {
    return imagePath;
  }
  
  // If it's an HTTP URL, also use as-is
  if (imagePath.startsWith('http://')) {
    return imagePath;
  }
  
  // Data URI - use as-is
  if (imagePath.startsWith('data:')) {
    return imagePath;
  }
  
  // Relative path from CSV - construct backend URL
  const cleanPath = imagePath.replace(/\\/g, '/').replace(/^\/+/, '');
  return `http://localhost:8007/images/${cleanPath}`;
}