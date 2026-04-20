# Stage 2. Transcription

## Objective

Convert an uploaded recording into a stored transcript.

## In Scope

- implement audio upload
- store `audio_storage_key`
- implement `STTAdapter`
- split transcript into segments
- store transcript segments
- move call status to `transcribed`

## Required Deliverables

- upload endpoint
- working STT adapter
- stored transcript

## Exit Criteria

Stage 2 is complete only when all of the following are true:

- audio can be uploaded for an existing `CallSession`
- the uploaded file is stored in the configured audio storage location
- `audio_storage_key` is persisted for the call
- transcription runs through `STTAdapter`
- transcript output is split into ordered `TranscriptSegment` records
- transcript segments are stored in the database
- the call transitions to `transcribed`
- the system returns transcript data together with status `transcribed`

## Readiness For Stage 3

Work may proceed to Stage 3 only when:

- the transcript pipeline is stable for the happy path
- transcript data is available for retrieval and later analysis
- exactly one STT provider is used behind the adapter interface

## Stage Constraints

- use one STT provider only
- keep transcription behind the adapter interface
