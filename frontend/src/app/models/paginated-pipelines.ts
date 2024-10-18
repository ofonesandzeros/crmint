import { Pipeline } from './pipeline';

export interface PaginatedPipelines {
  pipelines: Pipeline[];
  total: number;
  page: number;
  itemsPerPage: number;
}