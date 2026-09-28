import { useCallback, useEffect, useRef, useState } from 'react';
import { planDecision } from './api';
import type { GameViewResponse, HumanActionPlan } from './types';

const PLANNABLE = new Set([
  'choose_grit_action', 'choose_action_type', 'spend_link_for_extra_action',
  'choose_marketing_card', 'play_marketing_card', 'launch_poker',
]);

export function useHumanActionPlan(rawView: GameViewResponse | null, enabled: boolean) {
  const [stored, setStored] = useState<{ key: string; plan: HumanActionPlan } | null>(null);
  const [optionalKind, setOptionalKind] = useState<'link' | 'marketing' | 'poker' | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);
  const decision = rawView?.pending_decision;
  const key = rawView ? `${rawView.game_id}:${rawView.revision}:${decision?.decision_id}` : '';
  const active = enabled && !!decision && PLANNABLE.has(decision.decision_type);
  const plan = active && stored?.key === key ? stored.plan : null;
  const optional = plan?.optional.find((item) => item.kind === optionalKind);

  const stage = useCallback(async (selections: string[][] = []) => {
    const decision = rawView?.pending_decision;
    if (!rawView || !decision) return;
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const next = await planDecision(rawView.game_id, rawView.viewing_player_id, decision.decision_id, selections);
      if (id !== requestId.current) return;
      setStored({ key, plan: next });
      setOptionalKind(null);
    } catch (err) {
      if (id === requestId.current) setError(err instanceof Error ? err.message : String(err));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [rawView, key]);

  useEffect(() => {
    setOptionalKind(null);
    setStored(null);
    setError(null);
    if (active) void stage();
    else setLoading(false);
    const counter = requestId;
    return () => { counter.current++; };
    // A fresh authoritative decision invalidates every staged choice and in-flight preview.
  }, [stage, active]);

  return {
    plan,
    view: optional?.view ?? plan?.view ?? rawView,
    prefix: optional?.prefix ?? plan?.prefix ?? [],
    optionalKind: optional ? optionalKind : null,
    toggleOptional: (kind: 'link' | 'marketing' | 'poker') => setOptionalKind((current) => current === kind ? null : kind),
    loading: active && !error && (!plan || loading),
    error,
    stage,
  };
}
