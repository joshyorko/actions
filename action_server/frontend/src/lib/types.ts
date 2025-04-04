/* eslint-disable camelcase */
import type { OpenAPIV3_1 } from 'openapi-types';

export interface ActionPackage {
  id: string;
  name: string;
  actions: Action[];
}

export interface Action {
  id: string; // primary key (uuid)
  action_package_id: string; // foreign key to the action package
  name: string; // The action name
  docs: string; // Docs for the action
  enabled: boolean; // Is the action available to be run

  // File for the action (relative to the directory in the ActionPackage).
  file: string;
  lineno: number; // Line for the action
  input_schema: string; // The json content for the schema input
  output_schema: string; // The json content for the schema output
  managed_params_schema?: string; // The json content for the managed parameters.
}

export enum RunStatus {
  'NOT_RUN' = 0,
  'RUNNING' = 1,
  'PASSED' = 2,
  'FAILED' = 3,
  'CANCELLED' = 4,
}

export interface Run {
  id: string; // primary key (uuid)
  status: RunStatus; // 0=not run, 1=running, 2=passed, 3=failed
  action_id: string; // foreign key to the action
  start_time: string; // The time of the run creation.
  run_time?: number | null; // The time from the run creation to the run finish (in seconds)
  inputs: string; // The json content with the variables used as an input
  result?: string | null; // The json content of the output that the run generated
  error_message?: string | null; // If the status=failed, this may have an error message
  numbered_id: number;
}

export interface RunTableEntry extends Run {
  action?: Action;
}

export type Artifact = Record<string, string>;

export interface AsyncLoaded<T> {
  data?: T;
  isPending?: boolean;
  errorMessage?: string;
}

export type LoadedRuns = AsyncLoaded<Run[]>;
export type LoadedActionsPackages = AsyncLoaded<ActionPackage[]>;
export type LoadedArtifacts = AsyncLoaded<Artifact>;
export type LoadedServerConfig = AsyncLoaded<ServerConfig>;

export interface InputProperty {
  type: OpenAPIV3_1.NonArraySchemaObjectType | 'enum' | 'array';
  description: string;
  title: string;
  default?: string;
}

export type ServerConfig = {
  expose_url: string;
  auth_enabled: boolean;
  version: string; // The version for the action server (if it changes a full window reload would be needed).
  mtime_uuid: string; // The mtime of the action server (if it changes all data needs to be reloaded).
};
