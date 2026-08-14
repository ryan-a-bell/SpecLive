/**
 * Typed API client for the Requirements Discovery Copilot backend.
 *
 * Every response is parsed with the shared Zod schemas, so callers receive
 * validated, fully-typed data. The client holds no UI or business logic.
 */
import {
  Coverage,
  ConversationGraph,
  DiscoveryArtifact,
  DiscoverySession,
  DiscoveryTree,
  EvidenceLink,
  Recommendations,
  ScriptState,
  TranscriptSegment,
  TranscriptionCapability,
  type ArtifactType,
  type EvidenceRelationship,
  type Speaker,
  TranscriptionServerFrame,
} from "@rdc/domain";
import { z } from "zod";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ClientOptions {
  baseUrl: string;
  fetchImpl?: typeof fetch;
}

export function createClient({ baseUrl, fetchImpl }: ClientOptions) {
  const doFetch = fetchImpl ?? fetch;
  const root = baseUrl.replace(/\/$/, "");
  const socketRoot = root.replace(/^http/, "ws");

  async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
    const res = await doFetch(`${root}/api/v1${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, detail);
    }
    return schema.parse(await res.json());
  }

  async function requestText(path: string, init?: RequestInit): Promise<string> {
    const res = await doFetch(`${root}/api/v1${path}`, init);
    if (!res.ok) throw new ApiError(res.status, res.statusText);
    return res.text();
  }

  return {
    // sessions
    listSessions: () => request("/sessions", z.array(DiscoverySession)),
    getSession: (id: string) => request(`/sessions/${id}`, DiscoverySession),
    createSession: (body: {
      title: string;
      customer: string;
      facilitator: string;
      script_id?: string;
    }) =>
      request("/sessions", DiscoverySession, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    // transcript
    getTranscript: (id: string) =>
      request(`/sessions/${id}/transcript`, z.array(TranscriptSegment)),
    addSegment: (id: string, body: { speaker: Speaker; text: string }) =>
      request(`/sessions/${id}/transcript`, TranscriptSegment, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    transcriptionSocketUrl: (id: string) =>
      `${socketRoot}/api/v1/sessions/${encodeURIComponent(id)}/audio`,
    parseTranscriptionFrame: (data: string) => TranscriptionServerFrame.parse(JSON.parse(data)),
    getTranscriptionCapability: () => request("/transcription/status", TranscriptionCapability),

    // artifacts + evidence
    listArtifacts: (id: string) => request(`/sessions/${id}/artifacts`, z.array(DiscoveryArtifact)),
    getArtifact: (artifactId: string) => request(`/artifacts/${artifactId}`, DiscoveryArtifact),
    getEvidence: (artifactId: string) =>
      request(`/artifacts/${artifactId}/evidence`, z.array(EvidenceLink)),
    getSessionEvidence: (id: string) => request(`/sessions/${id}/evidence`, z.array(EvidenceLink)),
    createArtifact: (
      id: string,
      body: { artifact_type: ArtifactType; title: string; statement: string; confidence?: number },
    ) =>
      request(`/sessions/${id}/artifacts`, DiscoveryArtifact, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patchArtifact: (
      artifactId: string,
      body: Partial<{
        title: string;
        statement: string;
        confidence: number;
        change_reason: string;
      }>,
    ) =>
      request(`/artifacts/${artifactId}`, DiscoveryArtifact, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    addEvidence: (
      artifactId: string,
      body: {
        transcript_segment_id: string;
        quote_start: number;
        quote_end: number;
        quoted_text: string;
        relationship?: EvidenceRelationship;
      },
    ) =>
      request(`/artifacts/${artifactId}/evidence`, EvidenceLink, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    confirmArtifact: (artifactId: string) =>
      request(`/artifacts/${artifactId}/confirm`, DiscoveryArtifact, { method: "POST" }),
    rejectArtifact: (artifactId: string, reason?: string) =>
      request(`/artifacts/${artifactId}/reject`, DiscoveryArtifact, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    mergeArtifact: (artifactId: string, intoArtifactId: string) =>
      request(`/artifacts/${artifactId}/merge`, DiscoveryArtifact, {
        method: "POST",
        body: JSON.stringify({ into_artifact_id: intoArtifactId }),
      }),

    // projections
    getDiscoveryTree: (id: string) => request(`/sessions/${id}/discovery-tree`, DiscoveryTree),
    getConversationGraph: (id: string) =>
      request(`/sessions/${id}/conversation-graph`, ConversationGraph),
    getCoverage: (id: string) => request(`/sessions/${id}/coverage`, Coverage),
    getRecommendations: (id: string) => request(`/sessions/${id}/recommendations`, Recommendations),

    // script
    getScriptState: (id: string) => request(`/sessions/${id}/script`, ScriptState),
    advanceScript: (id: string) =>
      request(`/sessions/${id}/script/advance`, ScriptState, { method: "POST" }),

    // analysis + export
    analyze: (id: string) =>
      request(`/sessions/${id}/analyze`, z.array(DiscoveryArtifact), { method: "POST" }),
    exportPackage: (id: string, format: "json" | "markdown") =>
      requestText(`/sessions/${id}/export?format=${format}`),
  };
}

export type ApiClient = ReturnType<typeof createClient>;
export { ApiError as RdcApiError };
