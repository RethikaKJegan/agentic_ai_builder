import {z} from 'zod';
import {businessVersionSchema} from './business-ontology';

const sourceMapping=z.object({id:z.string(),concept_id:z.string(),source_role:z.string(),collection:z.string(),field_path:z.string(),attribute:z.string().optional()});

// Projection of the existing knowledge inspection response, not a new ontology.
export const knowledgeSnapshotSchema=businessVersionSchema.pick({version_id:true,revision:true,concepts:true,relationships:true,rules:true}).extend({
  source_mappings:z.array(sourceMapping).optional(),
  knowledge:z.object({source_mappings:z.array(sourceMapping).default([])}).passthrough().nullable().optional(),
});
export type KnowledgeSnapshot=z.infer<typeof knowledgeSnapshotSchema>;
