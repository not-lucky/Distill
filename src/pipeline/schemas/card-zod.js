import { z } from 'zod';

const CardItemSchema = z.object({
  card_format: z
    .enum(['Basic', 'Cloze', 'MCQ'])
    .describe('The structural layout of the card in Anki.'),
  card_type: z
    .enum([
      'Concept',
      'Code',
      'Procedure',
      'Syntax',
      'Behavior',
      'Constraint',
      'ErrorHandling',
      'TradeOff',
    ])
    .describe('Pedagogical tag for sorting and styled headers.'),
  tags: z
    .array(z.string().regex(/^[A-Za-z0-9-_/]+$/))
    .describe('Alphanumeric, hyphen, underscore, and slash tags (no spaces allowed).'),
  front: z
    .string()
    .describe(
      'Front/question side of the card, or statement with {{c1::hidden text}} syntax for Cloze.',
    ),
  back: z
    .string()
    .nullable()
    .describe('Short, punchy answer. Required for Basic card format; prohibited in MCQ or Cloze.'),
  options: z
    .array(z.string())
    .min(2)
    .max(4)
    .nullable()
    .describe('2 to 4 choices. Required only for MCQ.'),
  correct_answer: z
    .enum(['A', 'B', 'C', 'D'])
    .nullable()
    .describe('Correct choice letter index. Required only for MCQ.'),
  explanation: z
    .string()
    .describe(
      'Detailed background explanation, code examples, or trade-offs shown on the back side of all card formats.',
    ),
});

export const CARD_ZOD_SCHEMA = z.object({
  title: z.string().describe('Title of the concept, problem, or document section.'),
  topic: z.string().describe('Main category hierarchy or path.'),
  difficulty: z
    .enum(['Basic', 'Intermediate', 'Advanced'])
    .describe('Standardized difficulty level for database sorting.'),
  cards: z.array(CardItemSchema),
});

const CardTypeSchema = z.enum([
  'Concept',
  'Code',
  'Procedure',
  'Syntax',
  'Behavior',
  'Constraint',
  'ErrorHandling',
  'TradeOff',
]);

const BasicCardSchema = z
  .object({
    card_format: z.literal('Basic'),
    card_type: CardTypeSchema,
    tags: z.array(z.string().regex(/^[A-Za-z0-9-_/]+$/)),
    front: z.string(),
    back: z.string(),
    explanation: z.string(),
  })
  .strict();

const ClozeCardSchema = z
  .object({
    card_format: z.literal('Cloze'),
    card_type: CardTypeSchema,
    tags: z.array(z.string().regex(/^[A-Za-z0-9-_/]+$/)),
    front: z.string().refine((val) => /\{\{c[0-9]+::/.test(val), {
      message: 'front must contain at least one cloze deletion using {{c1::word}} syntax.',
    }),
    explanation: z.string(),
  })
  .strict();

const MCQCardSchema = z
  .object({
    card_format: z.literal('MCQ'),
    card_type: CardTypeSchema,
    tags: z.array(z.string().regex(/^[A-Za-z0-9-_/]+$/)),
    front: z.string(),
    options: z.array(z.string()).min(2).max(4),
    correct_answer: z.enum(['A', 'B', 'C', 'D']),
    explanation: z.string(),
  })
  .strict()
  .superRefine((data, ctx) => {
    if (data.correct_answer === 'C' && (!data.options || data.options.length < 3)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'options must NOT have fewer than 3 items when correct_answer is C',
        path: ['options'],
      });
    }
    if (data.correct_answer === 'D' && (!data.options || data.options.length < 4)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'options must NOT have fewer than 4 items when correct_answer is D',
        path: ['options'],
      });
    }
  });

const ValidationCardSchema = z.discriminatedUnion('card_format', [
  BasicCardSchema,
  ClozeCardSchema,
  MCQCardSchema,
]);

export const CARD_VALIDATION_SCHEMA = z
  .object({
    title: z.string(),
    topic: z.string(),
    difficulty: z.enum(['Basic', 'Intermediate', 'Advanced']),
    cards: z.array(ValidationCardSchema),
  })
  .strict();
