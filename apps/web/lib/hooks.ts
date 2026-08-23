"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

const keys = {
  sessions: ["sessions"] as const,
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
  scripts: ["scripts"] as const,
  transcriptionCapability: ["transcription-capability"] as const,
  analysisSettings: ["analysis-settings"] as const,
  storageSettings: ["storage-settings"] as const,
};

export function useSessions() {
  return useQuery({
    queryKey: keys.sessions,
    queryFn: () => api.listSessions(),
    staleTime: 15_000,
  });
}

export function useSession(id: string) {
  return useQuery({ queryKey: keys.session(id), queryFn: () => api.getSession(id) });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.createSession>[0]) => api.createSession(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.sessions }),
  });
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

export function useScripts() {
  return useQuery({
    queryKey: keys.scripts,
    queryFn: () => api.listScripts(),
    staleTime: 60_000,
  });
}

export function useCreateScript() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.createScript>[0]) => api.createScript(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.scripts }),
  });
}

export function useUpdateScript() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      scriptId,
      body,
    }: {
      scriptId: string;
      body: Parameters<typeof api.updateScript>[1];
    }) => api.updateScript(scriptId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.scripts }),
  });
}

export function useArchiveScript() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scriptId: string) => api.archiveScript(scriptId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.scripts }),
  });
}

export function useSetSessionScript(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (scriptId: string) => api.patchSession(sessionId, { script_id: scriptId }),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: keys.session(sessionId) }),
        queryClient.invalidateQueries({ queryKey: keys.script(sessionId) }),
        queryClient.invalidateQueries({ queryKey: keys.recommendations(sessionId) }),
        queryClient.invalidateQueries({ queryKey: keys.coverage(sessionId) }),
      ]),
  });
}

export function useTranscriptionCapability() {
  return useQuery({
    queryKey: keys.transcriptionCapability,
    queryFn: api.getTranscriptionCapability,
    staleTime: 30_000,
  });
}

export function useAnalysisSettings() {
  return useQuery({
    queryKey: keys.analysisSettings,
    queryFn: api.getAnalysisSettings,
    staleTime: 60_000,
  });
}

export function useStorageSettings() {
  return useQuery({
    queryKey: keys.storageSettings,
    queryFn: api.getStorageSettings,
    staleTime: 60_000,
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

/**
 * Confirm/reject an artifact from a workspace-level surface (the Validation
 * inbox), where each item belongs to a different conversation. The session id
 * travels with the mutation so the right conversation's queries are refreshed.
 */
export function useReviewActions() {
  const queryClient = useQueryClient();
  const invalidateSession = (sessionId: string) =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: keys.artifacts(sessionId) }),
      queryClient.invalidateQueries({ queryKey: keys.sessionEvidence(sessionId) }),
      queryClient.invalidateQueries({ queryKey: keys.tree(sessionId) }),
      queryClient.invalidateQueries({ queryKey: keys.coverage(sessionId) }),
      queryClient.invalidateQueries({ queryKey: keys.recommendations(sessionId) }),
    ]);
  const confirm = useMutation({
    mutationFn: (v: { artifactId: string; sessionId: string }) => api.confirmArtifact(v.artifactId),
    onSuccess: (_data, v) => invalidateSession(v.sessionId),
  });
  const reject = useMutation({
    mutationFn: (v: { artifactId: string; sessionId: string }) => api.rejectArtifact(v.artifactId),
    onSuccess: (_data, v) => invalidateSession(v.sessionId),
  });
  return { confirm, reject };
}

export { keys as queryKeys };
