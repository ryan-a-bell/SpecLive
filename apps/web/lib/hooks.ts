"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

const keys = {
  session: (id: string) => ["session", id] as const,
  transcript: (id: string) => ["transcript", id] as const,
  artifacts: (id: string) => ["artifacts", id] as const,
  sessionEvidence: (id: string) => ["session-evidence", id] as const,
  evidence: (id: string | null) => ["evidence", id] as const,
  tree: (id: string) => ["discovery-tree", id] as const,
  graph: (id: string) => ["conversation-graph", id] as const,
  coverage: (id: string) => ["coverage", id] as const,
  recommendations: (id: string) => ["recommendations", id] as const,
  script: (id: string) => ["script", id] as const,
  transcriptionCapability: ["transcription-capability"] as const,
};

export function useSession(id: string) {
  return useQuery({ queryKey: keys.session(id), queryFn: () => api.getSession(id) });
}

export function useTranscript(id: string) {
  return useQuery({ queryKey: keys.transcript(id), queryFn: () => api.getTranscript(id) });
}

export function useArtifacts(id: string) {
  return useQuery({ queryKey: keys.artifacts(id), queryFn: () => api.listArtifacts(id) });
}

export function useSessionEvidence(id: string) {
  return useQuery({
    queryKey: keys.sessionEvidence(id),
    queryFn: () => api.getSessionEvidence(id),
  });
}

export function useEvidence(artifactId: string | null) {
  return useQuery({
    queryKey: keys.evidence(artifactId),
    queryFn: () => api.getEvidence(artifactId!),
    enabled: Boolean(artifactId),
  });
}

export function useDiscoveryTree(id: string) {
  return useQuery({ queryKey: keys.tree(id), queryFn: () => api.getDiscoveryTree(id) });
}

export function useConversationGraph(id: string) {
  return useQuery({ queryKey: keys.graph(id), queryFn: () => api.getConversationGraph(id) });
}

export function useCoverage(id: string) {
  return useQuery({ queryKey: keys.coverage(id), queryFn: () => api.getCoverage(id) });
}

export function useRecommendations(id: string) {
  return useQuery({
    queryKey: keys.recommendations(id),
    queryFn: () => api.getRecommendations(id),
  });
}

export function useScriptState(id: string) {
  return useQuery({ queryKey: keys.script(id), queryFn: () => api.getScriptState(id) });
}

export function useTranscriptionCapability() {
  return useQuery({
    queryKey: keys.transcriptionCapability,
    queryFn: api.getTranscriptionCapability,
    staleTime: 30_000,
  });
}

function useInvalidateSession(id: string) {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: keys.transcript(id) }),
      queryClient.invalidateQueries({ queryKey: keys.artifacts(id) }),
      queryClient.invalidateQueries({ queryKey: keys.sessionEvidence(id) }),
      queryClient.invalidateQueries({ queryKey: keys.tree(id) }),
      queryClient.invalidateQueries({ queryKey: keys.coverage(id) }),
      queryClient.invalidateQueries({ queryKey: keys.recommendations(id) }),
    ]);
  };
}

export function useAddSegment(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.addSegment>[1]) => api.addSegment(id, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.transcript(id) }),
  });
}

export function useCorrectTranscriptSpeaker(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      segmentId,
      ...body
    }: {
      segmentId: string;
      speaker: "facilitator" | "customer" | "participant" | "system" | "unknown";
      speaker_name: string;
      apply_to_voice: boolean;
    }) => api.correctTranscriptSpeaker(id, segmentId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.transcript(id) }),
  });
}

export function useAnalyze(id: string) {
  const invalidate = useInvalidateSession(id);
  return useMutation({ mutationFn: () => api.analyze(id), onSuccess: invalidate });
}

export function useAdvanceScript(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.advanceScript(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.script(id) }),
  });
}

export function useConfirmArtifact(sessionId: string) {
  const invalidate = useInvalidateSession(sessionId);
  return useMutation({ mutationFn: api.confirmArtifact, onSuccess: invalidate });
}

export function useRejectArtifact(sessionId: string) {
  const invalidate = useInvalidateSession(sessionId);
  return useMutation({ mutationFn: (id: string) => api.rejectArtifact(id), onSuccess: invalidate });
}

export { keys as queryKeys };
