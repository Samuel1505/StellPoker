/**
 * Client-side hand history capture/persistence for the current browser
 * session. Each table keeps its own localStorage entry so the viewer panel
 * can show completed hands (street-by-street pot/board progression, the
 * viewing player's own hole cards when known, final pot, winner, and the
 * settlement proof tx) even after a hand has ended.
 */

import { bestHandRank } from "./hand-rank";

export type Street = "preflop" | "flop" | "turn" | "river";

export interface StreetSnapshot {
  street: Street;
  pot: number;
  boardCards: number[];
}

export interface HandHistoryEntry {
  tableId: number;
  handNumber: number;
  timestamp: number;
  streets: StreetSnapshot[];
  finalPot: number;
  boardCards: number[];
  holeCards?: [number, number];
  handRankName?: string;
  winnerAddress?: string | null;
  txHash?: string;
}

const STORAGE_PREFIX = "stellpoker:hand-history:";
const MAX_ENTRIES_PER_TABLE = 50;

function storageKey(tableId: number): string {
  return `${STORAGE_PREFIX}${tableId}`;
}

export function loadHandHistory(tableId: number): HandHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey(tableId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as HandHistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export function saveHandHistoryEntry(entry: HandHistoryEntry): void {
  if (typeof window === "undefined") return;
  try {
    const existing = loadHandHistory(entry.tableId);
    const next = [entry, ...existing].slice(0, MAX_ENTRIES_PER_TABLE);
    window.localStorage.setItem(storageKey(entry.tableId), JSON.stringify(next));
  } catch {
    // Storage unavailable (private browsing, quota) — history just won't persist.
  }
}

export function buildHandRankName(
  holeCards: [number, number] | undefined,
  boardCards: number[]
): string | undefined {
  if (!holeCards) return undefined;
  return bestHandRank([...holeCards, ...boardCards])?.name;
}
