# Typing an Express app

---

### Setting up the project

Let's start by creating a new directory for our project and initializing it with *npm init*. We will also install Express and its type definitions:

```bash
npm install express
npm install --save-dev @types/express
```

Let's also install TypeScript as a development dependency:

```bash
npm install --save-dev typescript
```

We will also create a *tsconfig.json* file. The file should look like this:

```json
{
  "compilerOptions": {
    "target": "esnext",
    "noEmit": true,
    "module": "nodenext",
    "esModuleInterop": true,
    "allowImportingTsExtensions": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

Let's go through each configuration:

The *target: "esnext"* configures that TypeScript should compile to the latest JavaScript features. The compiled code will use cutting-edge JavaScript syntax. Because we use Node version 24, we are actually not compiling the code, so the target does not matter much.

The *noEmit: true* is already familliar to us, it tells compiler just to do the type checking without generating the compiled code.

*module: "nodenext"* tells TypeScript to use Node.js's native module resolution for ESM (ES Modules). In practice, this means that we can use the *import* syntax on module imports.

*esModuleInterop: true* enables compatibility between CommonJS and ES module import styles in TypeScript.

Without it, importing a CommonJS module requires `import * as express from 'express';`

With it, you can use `import express from 'express';` which is more natural.

*allowImportingTsExtensions: true* allows us to import TypeScript files using the `.ts` extension. This is useful when we want to be explicit about the file extension in our imports.

*strict: true* enables all strict type-checking options. This is recommended for all TypeScript projects.

*noUnusedLocals: true* reports errors on unused local variables. This helps keep the code clean.

*noUnusedParameters: true* reports errors on unused parameters. This helps keep the code clean.

*noImplicitReturns: true* reports errors for functions that don't return anything on all code paths. This helps catch potential bugs.

*noFallthroughCasesInSwitch: true* reports errors for fallthrough cases in switch statements. This helps catch potential bugs.

Let's also set up ESLint for our project. We will use the following packages:

```bash
npm install --save-dev eslint @eslint/js typescript-eslint @stylistic/eslint-plugin @types/express
```

Now our *package.json* should look like this:

```json
{
  "name": "flights",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "tsc": "tsc"
  },
  "author": "",
  "license": "ISC",
  "devDependencies": {
    "@eslint/js": "^10.0.1",
    "@stylistic/eslint-plugin": "^5.10.0",
    "@types/express": "^5.0.6",
    "eslint": "^10.1.0",
    "typescript": "^6.0.2",
    "typescript-eslint": "^8.57.2"
  },
  "dependencies": {
    "express": "^5.2.1"
  }
}
```

We also create a *eslint.config.mjs* file with the following content:

```javascript
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import stylistic from '@stylistic/eslint-plugin';

export default tseslint.config({
  files: ['**/*.ts'],
  extends: [
    eslint.configs.recommended,
    ...tseslint.configs.recommendedTypeChecked,
  ],
  languageOptions: {
    parserOptions: {
      projectService: true,
      tsconfigRootDir: import.meta.dirname,
    },
  },
  plugins: {
    '@stylistic': stylistic,
  },
  rules: {
    '@stylistic/semi': 'error',
    '@typescript-eslint/no-unsafe-assignment': 'error',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/restrict-template-expressions': 'off',
    '@typescript-eslint/restrict-plus-operands': 'off',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { argsIgnorePattern: '^_' },
    ],
  },
});
```

Now we just need to set up our development environment, and we are ready to start writing some serious code.

We will opt for the same option as previously, and run *tsc* and *node --watch* concurrently. Let us first install [concurrently](https://www.npmjs.com/package/concurrently):

```bash
npm install --save-dev concurrently
```

And then we modify our npm scripts in *package.json*:

```json
{
  "scripts": {
    "tsc": "tsc",
    "dev": "concurrently \"tsc --watch\" \"node --watch build/index.js\"",
    "start": "node build/index.js",
    "lint": "eslint ."
  }
}
```

### Let there be code

Let's start by creating a simple Express app. Create a file *index.ts* with the following content:

```typescript
import express from 'express';

const app = express();
app.use(express.json());

const PORT = 3000;

app.get('/ping', (_req, res) => {
  console.log('someone pinged here');
  res.send('pong');
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

Now, if we run the app with `npm run dev` or `npm start` we can verify that a request to [http://localhost:3000/ping](http://localhost:3000/ping) gives the response *pong*, so our configuration is set!

![Screenshot of a terminal window showing the Express server starting successfully on port 3000, with the message "Server running on port 3000" displayed. The terminal has a dark background with light-colored text, showing the Node.js process running without any errors.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/Zgw0V4ptTIau23q2vxPIgLWicdK8vJ.png)

There is one small thing, when we run the app with `npm run dev` we see a warning:

```
(node:1234) ExperimentalWarning: Watch mode is an experimental feature and might change at any time
(Use `node --trace-warnings ...` to show where the warning was created)
```

The warning could be silenced by adding the flag `--disable-warning=ExperimentalWarning`.

### A few words on running TypeScript with Node.js

As mentioned, Node's built-in TypeScript support works by stripping types, it simply removes type annotations and runs the remaining JavaScript. This is fast and sufficient for most TypeScript code. However, certain TypeScript features go beyond mere type annotations and require actual code transformation to work correctly at runtime.

The `--experimental-transform-types` flag enables Node.js to handle these features. Most notably, this includes [Enums](https://www.typescriptlang.org/docs/handbook/enums.html). TypeScript enums compile down to real JavaScript objects. Without transformation, Node would strip the enum syntax and leave behind invalid code.

Without this flag, using an enum in your code would cause a runtime error, even though your TypeScript type-checker reports no issues.

Despite not using any of these features for now, let us add the flag to the scripts:

```json
{
  // ...
  "scripts": {
    "tsc": "tsc",
    "dev": "concurrently \"tsc --watch\" \"node --watch --experimental-transform-types index.ts\"",
    "start": "node --experimental-transform-types index.ts",
    "lint": "eslint ."
  },
  // ...
}
```

When we run the app, we see a warning:

```
(node:80296) ExperimentalWarning: Transform Types is an experimental feature and might change at any time
(Use `node --trace-warnings ...` to show where the warning was created)
```

The warning could be silenced by adding the flag `--disable-warning=ExperimentalWarning`.

### Implementing the functionality

Let's start implementing the actual functionality of our application. We will create a simple flight diary application that allows users to create and view flight diary entries.

The data to be used in the exercises is in this [JSON file](https://raw.githubusercontent.com/fullstack-hy2020/flightdiary/main/data/entries.json):

```json
[
  {
    "id": 1,
    "date": "2026-01-01",
    "weather": "rainy",
    "visibility": "poor",
    "comment": "Pretty scary flight, I'm glad I'm alive"
  },
  {
    "id": 2,
    "date": "2026-04-01",
    "weather": "sunny",
    "visibility": "good",
    "comment": "Everything went better than expected, I'm learning much"
  },
  // ...
]
```

Let's start by creating an endpoint that returns all flight diary entries.

First, we need to make some decisions on how to structure our source code. It is better to place all source code under *src* directory, so source code is not mixed with configuration files. We will move *index.ts* there and make the necessary changes to the npm scripts.

We will place all [routers](https://fullstackopen.com/en/part4/structure_of_backend_application_introduction_to_testing) and modules which are responsible for handling a set of specific resources such as *diaries*, under the directory *src/routes*. This is a bit different than what we did in [part 4](https://fullstackopen.com/en/part4) of the Full Stack Open course.

Let's create a file *src/routes/diaries.ts* with the following content:

```typescript
import express from 'express';

const router = express.Router();

router.get('/', (_req, res) => {
  res.send('Fetching all diaries!');
});

router.post('/', (_req, res) => {
  res.send('Saving a diary!');
});

export default router;
```

We'll route all requests to prefix */api/diaries* to that specific router in *index.ts*:

```typescript
import express from 'express';
import diaryRouter from './routes/diaries.ts';

const app = express();
app.use(express.json());

const PORT = 3000;

app.use('/api/diaries', diaryRouter);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

Let's create a service for handling the diaries. Create a file *src/services/diaryService.ts*:

```typescript
const diaryData = [
  {
    id: 1,
    date: '2026-01-01',
    weather: 'rainy',
    visibility: 'poor',
    comment: 'Pretty scary flight, I\'m glad I\'m alive'
  },
  {
    id: 2,
    date: '2026-04-01',
    weather: 'sunny',
    visibility: 'good',
    comment: 'Everything went better than expected, I\'m learning much'
  },
];

const getAllDiaries = () => {
  return diaryData;
};

const addDiary = () => {
  return null;
};

export default {
  getAllDiaries,
  addDiary
};
```

This is needed since if you are importing something other than code, Node.js needs to know what kind of file you're importing. The *with { type: "json" }* syntax is a new feature in Node.js that allows us to import JSON files as modules.

Let's wire the service to the router:

```typescript
import express from 'express';
import diaryService from '../services/diaryService.ts';

const router = express.Router();

router.get('/', (_req, res) => {
  res.send(diaryService.getAllDiaries());
});

router.post('/', (_req, res) => {
  res.send('Saving a diary!');
});

export default router;
```

And indeed, we see the diaries in the endpoint:

![Screenshot of a browser window showing a JSON response from the /api/diaries endpoint. The response displays an array of diary entry objects with id, date, weather, visibility, and comment fields. The JSON is formatted with syntax highlighting showing the flight diary data.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/cWHOtoStGKNagbItVH6VVNPz08wQ8E.png)

But something is not right:

![Screenshot of a VSCode editor window showing TypeScript code with red squiggly error underlines. The error indicates a type mismatch where the imported JSON data is being assigned to a variable, demonstrating a common TypeScript typing issue when working with JSON imports. The diaryService.ts file shows type errors related to the diaryData array not being properly typed.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/ZUiLlWfytyQVuYWUtJMEMERwHyZRLz.png)

The compiler is not happy with our code. The problem is that the JSON data is not typed, and the compiler does not know what type of data we are dealing with.

As we remember from the previous part, we can give the data a type by defining a type for it. The JSON data is imported with the *with { type: "json" }* syntax, which is a new feature in Node.js that allows us to import JSON files as modules.

The compiler infers the type of the JSON data from the file itself. This means that the compiler knows the structure of the data, but it does not know the specific types of the fields.

As a result, the compiler warns us if we try to do something suspicious with the JSON data we handle. For example, if we are handling an array containing objects of a specific type, and we try to add an object that does not have all the fields the other objects have, or has type conflicts (for example, a number where there should be a string), the compiler can give us a warning.

Even though the compiler is pretty good at making sure we don't do anything unwanted, it is safer to define the types for the data ourselves.

Currently, we have a basic working TypeScript Express app, but there are barely any actual *typings* in the code. Since we know what type of data should be accepted for the *weather* and *visibility* fields, there is no reason for us not to include their types in the code.

### Defining the types

Earlier, we saw how the compiler can determine a variable's type from the value it is assigned. Similarly, the compiler can interpret large data sets consisting of objects and arrays:

![Screenshot of VSCode editor showing TypeScript type inference on a data array. When hovering over the diaryEntries variable, a tooltip displays the inferred type showing an array of objects with specific property types (id: number, date: string, weather: string, visibility: string, comment: string), demonstrating TypeScript's ability to infer complex data structure types.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/gRWS01GFgV7GcrF8T7iqiXG7Wt3Vj4.png)

Let's create a file for our types, *types.ts*, where we'll define all our types for this project.

First, let's type the *Weather* and *Visibility* values using a [union type](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#union-types) of the allowed strings:

```typescript
export type Weather = 'sunny' | 'rainy' | 'cloudy' | 'windy' | 'stormy';

export type Visibility = 'great' | 'good' | 'ok' | 'poor';
```

And, from there, we can continue by creating a DiaryEntry type, which will be an [interface](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#interfaces):

```typescript
export interface DiaryEntry {
  id: number;
  date: string;
  weather: Weather;
  visibility: Visibility;
  comment: string;
}
```

We can now try to type our imported JSON:

```typescript
import diaryData from '../../data/entries.json' with { type: "json" };
import type { DiaryEntry } from '../types.ts';

const diaries: DiaryEntry[] = diaryData;

const getEntries = (): DiaryEntry[]  => {
  return diaries;
};

const addDiary = () => {
  return null;
};

export default {
  getEntries,
  addDiary
};
```

But since the JSON already has its values declared, assigning a type for the data set results in an error:

![Screenshot of a VSCode editor showing a TypeScript type error. The error indicates that the weather field in the imported JSON data is incompatible with the DiaryEntry type - the JSON has weather as type 'string' while DiaryEntry expects the Weather union type. The error message shows the type mismatch between string and the Weather union type.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/nONIXAcMKqyZWJT0mUhAbwzjvRYyfG.png)

The end of the error message reveals the problem: the *weather* fields are incompatible. In *DiaryEntry*, we specified that its type is *Weather*, but the TypeScript compiler had inferred its type to be *string*.

We could fix the problem by doing a [type assertion](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-assertions). As we already [mentioned](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#bc2e1861-1334-4a2c-a678-03f486621ce7) type assertions should be done only if we are certain we know what we are doing!

If we assert the type of the variable *diaryData* to be *DiaryEntry* with the keyword *as*, everything should work:

```typescript
import diaryData from '../../data/entries.json' with { type: "json" };
import type { DiaryEntry } from '../types.ts';

const diaries: DiaryEntry[] = diaryData as DiaryEntry[];

const getEntries = (): DiaryEntry[]  => {
  return diaries;
};

const addDiary = () => {
  return null;
};

export default {
  getEntries,
  addDiary
};
```

We should never use type assertion unless there is no other way to proceed, as there is always the danger we assert an unfit type to an object and cause a nasty runtime error. While the compiler trusts you to know what you are doing when using *as*, by doing this, we are not using the full power of TypeScript but relying on the coder to secure the code.

In our case, we could change how we export our data so we can type it within the data file. Since we cannot use typings in a JSON file, we should convert the JSON file to a ts file *entries.ts*, which exports the typed data like so:

```typescript
import type { DiaryEntry } from "../src/types.ts";

const diaryEntries: DiaryEntry[] = [
  {
      "id": 1,
      "date": "2026-01-01",
      "weather": "rainy",
      "visibility": "poor",
      "comment": "Pretty scary flight, I'm glad I'm alive"
  },
  // ...
];

export default diaryEntries;
```

Now, when we import the array, the compiler interprets it correctly:

```typescript
import diaries from '../../data/entries.ts';
import type { DiaryEntry } from '../types.ts';

const getEntries = (): DiaryEntry[] => {
  return diaries;
}

const addDiary = () => {
  return null;
}

export default {
  getEntries,
  addDiary
};
```

Note that, if we want to be able to save entries without a certain field, e.g. *comment*, we could set the type of the field as [optional](https://www.typescriptlang.org/docs/handbook/2/objects.html#optional-properties) by adding *?* to the type declaration:

```typescript
export interface DiaryEntry {
  id: number;
  date: string;
  weather: Weather;
  visibility: Visibility;
  comment?: string;
}
```

> **import type**
>
> When importing a type it is not enough to just do
>
> ```typescript
> import { DiaryEntry } from '../types.ts';
> ```
>
> We must instead do a [type only import](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-8.html#type-only-imports-and-export)
>
> ```typescript
> import type { DiaryEntry } from '../types.ts';
> ```
>
> When running TypeScript files directly with Node.js, TypeScript's type information is stripped at runtime. This means that if you import something that only exists as a type, like an interface or type alias, and you don't mark it explicitly with *import type,* the runtime may attempt to resolve it as a real JavaScript value and fail.
>
> Using *import type* tells both the TypeScript compiler and the runtime transform that this import exists purely for type-checking purposes and should be completely erased before execution.
>
> Fortunately, there is an ESLint rule [consistent-type-imports](https://typescript-eslint.io/rules/consistent-type-imports/) that helps us not to forget using import type. Let us enable the rule in *eslint.config.mjs*:
>
> ```javascript
> rules: {
>   // ...
>   "@typescript-eslint/consistent-type-imports": "error",
> },
> ```
>
> Now we are warned on omissions!

---

### Utility Types

Sometimes, we might want to use a specific modification of a type. For example, consider a page for listing some data, some of which is sensitive and some of which is non-sensitive. We might want to be sure that no sensitive data is used or displayed. We could *pick* the fields of a type we allow to be used to enforce this. We can do that by using the utility type [Pick](https://www.typescriptlang.org/docs/handbook/utility-types.html#picktype-keys).

In our project, we should consider that Ilari might want to create a listing of all his diary entries *excluding* the comment field since, during a very scary flight, he might end up writing something he wouldn't necessarily want to show to anyone else.

The [Pick](https://www.typescriptlang.org/docs/handbook/utility-types.html#picktype-keys) utility type allows us to choose which fields of an existing type we want to use. Pick can be used to either construct a completely new type or to inform a function of what it should return on runtime. Utility types are a special kind of type, but they can be used just like regular types.

In our case, to create a "censored" version of the *DiaryEntry* for public displays, we can use *Pick* in the function declaration:

```typescript
const getNonSensitiveEntries =
  (): Pick<DiaryEntry, 'id' | 'date' | 'weather' | 'visibility'>[] => {
    // ...
  }
```

and the compiler would expect the function to return an array of values of the modified *DiaryEntry* type, which includes only the four selected fields.

In this case, we want to exclude only one field, so it would be even better to use the [Omit](https://www.typescriptlang.org/docs/handbook/utility-types.html#omittype-keys) utility type, which we can use to declare which fields to exclude:

```typescript
const getNonSensitiveEntries = (): Omit<DiaryEntry, 'comment'>[] => {
  // ...
}
```

To improve the readability, we should most definitively define a [type alias](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-aliases) *NonSensitiveDiaryEntry* in the file *types.ts*:

```typescript
export type NonSensitiveDiaryEntry = Omit<DiaryEntry, 'comment'>;
```

The code changes like this:

```typescript
import diaries from '../../data/entries.ts';
import type { NonSensitiveDiaryEntry, DiaryEntry } from '../types.ts';

const getEntries = (): DiaryEntry[] => {
  return diaries;
};

const getNonSensitiveEntries = (): NonSensitiveDiaryEntry[] => {
  return diaries;
};

const addDiary = () => {
  return null;
};

export default {
  getEntries,
  addDiary,
  getNonSensitiveEntries
};
```

One thing in our application is a cause for concern. In *getNonSensitiveEntries*, we are returning the complete diary entries, and *no error is given* despite typing!

This happens because [TypeScript only checks](http://www.typescriptlang.org/docs/handbook/type-compatibility.html) whether we have all of the required fields or not, but excess fields are not prohibited. In our case, this means that it is *not prohibited* to return an object of type *DiaryEntry[]*, but if we were to try to access the *comment* field, it would not be possible because we would be accessing a field that TypeScript is unaware of even though it exists.

Unfortunately, this can lead to unwanted behavior if you are not aware of what you are doing; the situation is valid as far as TypeScript is concerned, but you are most likely allowing a use that is not wanted. If we were now to return all of the diary entries from the *getNonSensitiveEntries* function to the frontend, we would be *leaking the unwanted fields to the requesting browser* - even though our types seem to imply otherwise!

Because TypeScript doesn't modify the actual data but only its type, we need to exclude the fields ourselves:

```typescript
import diaries from '../../data/entries.ts'
import type { NonSensitiveDiaryEntry, DiaryEntry } from '../types.ts'

const getEntries = () : DiaryEntry[] => {
  return diaries
}

const getNonSensitiveEntries = (): NonSensitiveDiaryEntry[] => {
  return diaries.map(({ id, date, weather, visibility }) => ({
    id,
    date,
    weather,
    visibility,
  }));
};

const addDiary = () => {
  return null;
}

export default {
  getEntries,
  getNonSensitiveEntries,
  addDiary
}
```

Utility types include many handy tools, and it is undoubtedly worth it to take some time to study [the documentation](https://www.typescriptlang.org/docs/handbook/utility-types.html).

Let us now change the route to return only the nonsensitive diary data:

```typescript
import express from 'express';
import diaryService from '../services/diaryService.ts';

const router = express.Router();

router.get('/', (_req, res) => {
  res.send(diaryService.getNonSensitiveEntries());
});

router.post('/', (_req, res) => {
  res.send('Saving a diary!');
});

export default router;
```

The response is what we expect it to be:

![Screenshot of a browser window showing a JSON response from the /api/diaries endpoint. The response contains an array of diary entry objects with only the id, date, weather, and visibility fields - the comment field has been excluded. Each entry shows flight diary data like id: 1, date: "2026-01-01", weather: "rainy", visibility: "poor".](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/emutzmdmubeMuEaEH7iEXWDTk18lEI.png)

### Typing the request and response

So far we have not discussed anything about the types of the route handler parameters.

If we hover, for example, over the parameter *res*, we notice it has the following type:

```typescript
Response<any, Record<string, any>, number>
```

It looks a bit weird. The type *Response* is a [generic type](https://www.typescriptlang.org/docs/handbook/2/generics.html#generic-types) that has three *type parameters*. If we open the type definition (by right clicking and selecting *Go to Type Definition* in the VS code) we see the following:

```typescript
export interface Response<
    ResBody = any,
    LocalsObj extends Record<string, any> = Record<string, any>,
    StatusCode extends number = number,
> extends http.ServerResponse, Express.Response {
```

The first type parameter is the most interesting for us, it corresponds *the response body* and has a default value *any*. So that is why TypeScript compiler accepts any type of response and we get no help to get the response right.

We could and probably should give a proper type as the type variable. In our case, it is an array of diary entries:

```typescript
import express, { type Response } from 'express';
import type { NonSensitiveDiaryEntry } from "../types.ts";

// ...

router.get('/', (_req, res: Response<NonSensitiveDiaryEntry[]>) => {
  res.send(diaryService.getNonSensitiveEntries());
});

// ...
```

If we now try to respond with the wrong type of data, we get a type error:

![Screenshot of VSCode editor showing a TypeScript type error on a res.send() call. The error indicates that the argument type is not assignable to the Response type parameter NonSensitiveDiaryEntry[], demonstrating how TypeScript catches incorrect response types when proper generics are specified.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/FtXA6pQrwpWqp1NxkYrg3Djb8MmwsL.png)

Similarly the request parameter has the type *Request* that is also a generic type. We shall have a closer look at it later on.

---

## Exercise 9. Patientor backend, step1

> **Tries:** 1 | **Points:** 0/1
>
> For this set of exercises, you will develop a backend for an existing project called Patientor, a simple medical record application for doctors who handle diagnoses and basic health information for their patients. Outsider experts have already built the [frontend](https://github.com/fullstack-hy2020/patientor), and your task is to create a backend to support the existing code.
>
> Make sure that the frontend code is in the directory *patientor/frontend* of your submission repository.
>
> Initialize a backend project in the directory *patientor/backend* that will work with the frontend. Configure ESLint and tsconfig using the same settings as provided in the material.
>
> Define an endpoint that handles HTTP GET requests at the route */api/ping*.
>
> The project should be runnable with npm scripts, both in development mode with `npm run dev` and, in production mode with `npm start`.

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

## Exercise 10. Patientor backend, step2

> **Tries:** 1 | **Points:** 0/1
>
> Make sure you have copied the frontend code to the directory *patientor/frontend* of your submission repository. Start the project with the help of the README file. You should be able to use the frontend without a functioning backend.
>
> Ensure that the backend answers the ping request that the frontend has made on startup. Check the developer tools to make sure it works:
>
> ![Screenshot of browser developer tools showing the Network tab. A request to /api/ping is highlighted, showing a successful 200 OK response with "pong" as the response body. This confirms the backend ping endpoint is working correctly and the frontend can communicate with it.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/PngggqtjpGLWkxdBorhV3CUcIWhucZ.png)

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

## Exercise 11. Patientor backend, step3

> **Tries:** 1 | **Points:** 0/1
>
> Similar to Ilari's flight service, we do not use a real database in our app, but instead use hardcoded data that is in the files [diagnoses.ts](https://github.com/fullstack-hy2020/misc/blob/master/diagnoses.ts) and [patients.ts](https://github.com/fullstack-hy2020/misc/blob/master/patients.ts). Get the files and store those in a directory called *data* in your project. All data modification can be done in runtime memory, so during this part, it is *not necessary to write to a file*.
>
> Create a type *Diagnosis* and use it to create endpoint */api/diagnoses* for fetching all diagnoses with HTTP GET.
>
> Structure your code properly by using meaningfully-named directories and files.
>
> **Note** that *diagnoses* may or may not contain the field *latin*. You might want to use [optional properties](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#optional-properties) in the type definition.
>
> **Hint:** Enabling the ESLint rule [consistent-type-imports](https://typescript-eslint.io/rules/consistent-type-imports/) could save you from many headaches.

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

## Exercise 12. Patientor backend, step4

> **Tries:** 1 | **Points:** 0/1
>
> Create data type *Patient* and set up the GET endpoint */api/patients* which returns all the patients to the frontend, excluding field *ssn*. Use a [utility type](https://www.typescriptlang.org/docs/handbook/utility-types.html) to make sure you are selecting and returning only the wanted fields.
>
> In this exercise, you may assume that field *gender* has type *string*.
>
> Try the endpoint with your browser and ensure that *ssn* is not included in the response:
>
> ![Screenshot of a browser window showing a JSON response from the /api/patients endpoint. The response contains an array of patient objects with fields like id, name, dateOfBirth, gender, and occupation - but notably the ssn (social security number) field is excluded from each patient object, demonstrating proper use of TypeScript utility types to filter sensitive data.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/WivaSVyprR7NuhOZWQx7l5lyzFRaYN.png)
>
> After creating the endpoint, ensure that the *frontend* shows the list of patients:
>
> ![Screenshot of the Patientor frontend application showing a list of patients in a table or card layout. The patient list displays names, dates of birth, and other non-sensitive patient information fetched from the backend API. The UI has a clean medical application design.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/BokdkzZWA9uqC9JJHIcpcpqBJmGYmS.png)

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

### Preventing an accidental undefined result

Let's extend the backend to support fetching one specific entry with an HTTP GET request to route *api/diaries/:id*.

The DiaryService needs to be extended with a *findById* function:

```typescript
// ...

const findById = (id: number): DiaryEntry => {
  const entry = diaries.find(d => d.id === id);
  return entry;
};

export default {
  getEntries,
  getNonSensitiveEntries,
  addDiary,
  findById
}
```

But once again, a new problem emerges:

![Screenshot of VSCode editor showing a TypeScript type error on a return statement. The error indicates that the return type 'DiaryEntry | undefined' is not assignable to the declared return type 'DiaryEntry', because Array.find() can return undefined if no matching element is found.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/sJ89Lk5GPx56tO2bJbqTLE10dIzmWF.png)

The issue is that there is no guarantee that an entry with the specified id can be found. It is good that we are made aware of this potential problem already at the compile phase. Without TypeScript, we would not be warned about this problem, and in the worst-case scenario, we could have ended up returning an *undefined* object instead of informing the user about the specified entry not being found.

First of all, in cases like this, we need to decide what the *return value* should be if an object is not found, and how the case should be handled. The *find* method of an array returns *undefined* if the object is not found, and this is fine. We can solve our problem by typing the return value as follows:

```typescript
const findById = (id: number): DiaryEntry | undefined => {
  const entry = diaries.find(d => d.id === id);
  return entry;
}
```

The route handler is the following:

```typescript
import express from 'express';
import diaryService from '../services/diaryService.ts'

router.get('/:id', (req, res) => {
  const diary = diaryService.findById(Number(req.params.id));

  if (diary) {
    res.send(diary);
  } else {
    res.sendStatus(404);
  }
});

// ...

export default router;
```

---

### Adding a new diary

Let's start building the HTTP POST endpoint for adding new flight diary entries. The new entries should have the same type as the existing data.

The code handling of the response looks as follows:

```typescript
router.post('/', (req, res) => {
  const { date, weather, visibility, comment } = req.body;
  const addedEntry = diaryService.addDiary({
    date,
    weather,
    visibility,
    comment,
  });
  res.json(addedEntry);
})
```

So the code just destructures the parameters from the request body, and puts those into an object that is given as a parameter to the function *addDiary* of the *diaryService*.

But wait, what is the type of this object? It is not exactly a *DiaryEntry*, since it is still missing the *id* field. It could be useful to create a new type, *NewDiaryEntry*, for an entry that hasn't been saved yet. Let's create that in *types.ts* using the existing *DiaryEntry* type and the [Omit](https://www.typescriptlang.org/docs/handbook/utility-types.html#omittype-keys) utility type:

```typescript
export type NewDiaryEntry = Omit<DiaryEntry, 'id'>;
```

Now we can use the new type in our *diaryService*, and destructure the new entry object when creating an entry to be saved:

```typescript
import type { NewDiaryEntry, NonSensitiveDiaryEntry, DiaryEntry } from '../types';

// ...

const addDiary = ( entry: NewDiaryEntry ): DiaryEntry => {
  const newDiaryEntry = {
    id: Math.max(...diaries.map(d => d.id)) + 1,
    ...entry
  };

  diaries.push(newDiaryEntry);
  return newDiaryEntry;
};
```

There is lots of red in our editor:

![Screenshot of a VSCode editor window showing extensive red squiggly error underlines throughout TypeScript code. Multiple ESLint and TypeScript errors are visible, particularly around the req.body destructuring assignment, demonstrating type safety issues when handling untyped request body data in Express. The errors are caused by the @typescript-eslint/no-unsafe-assignment rule.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/0TOc3BFkt8nZ0oZNCJpPXKh1bTuOr6.png)

The cause is the ESlint rule [@typescript-eslint/no-unsafe-assignment](https://github.com/typescript-eslint/typescript-eslint/blob/master/packages/eslint-plugin/docs/rules/no-unsafe-assignment.md) that prevents us from assigning the fields of a request body to variables.

For the time being, let us just ignore the ESlint rule from the whole file by adding the following as the first line of the file:

```typescript
/* eslint-disable @typescript-eslint/no-unsafe-assignment */
```

To parse the incoming data we must have the *json* middleware configured:

```typescript
import express from 'express';
import diaryRouter from './routes/diaries.ts';
const app = express();
app.use(express.json());
const PORT = 3000;

app.use('/api/diaries', diaryRouter);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

Now the application is ready to receive HTTP POST requests for new diary entries of the correct type!

---

### Validating requests

There are plenty of things that can go wrong when we accept data from outside sources. Applications rarely work completely on their own, and we are forced to live with the fact that data from sources outside of our system cannot be fully trusted. When we receive data from an outside source, there is no way it can already be typed when we receive it. We need to make decisions on how to handle the uncertainty that comes with this.

The disabled ESlint rule was hinting to us that the following assignment is risky:

```typescript
const newDiaryEntry = diaryService.addDiary({
  date,
  weather,
  visibility,
  comment,
});
```

We would like to have the assurance that the object in a POST request has the correct type. Let us now define a function *parseNewDiaryEntry* that receives the request body as a parameter and returns a properly-typed *NewDiaryEntry* object. The function shall be defined in the file *utils.ts*.

The route definition uses the function as follows:

```typescript
import parseNewDiaryEntry from '../utils.ts';

// ...

router.post('/', (req, res) => {
  try {
    const newDiaryEntry = parseNewDiaryEntry(req.body);
    const addedEntry = diaryService.addDiary(newDiaryEntry);
    res.json(addedEntry);
  } catch (error: unknown) {
    let errorMessage = 'Something went wrong.';
    if (error instanceof Error) {
      errorMessage += ' Error: ' + error.message;
    }
    res.status(400).send(errorMessage);
  }
})
```

We can now also remove the first line that ignores the ESLint rule *no-unsafe-assignment*.

Since we are now writing secure code and trying to ensure that we are getting exactly the data we want from the requests, we should get started with parsing and validating each field we are expecting to receive.

The skeleton of the function *parseNewDiaryEntry* looks like the following:

```typescript
import type { NewDiaryEntry } from './types.ts';

const parseNewDiaryEntry = (object): NewDiaryEntry => {
  const newEntry: NewDiaryEntry = {
    // ...
  };

  return newEntry;
};

export default parseNewDiaryEntry;
```

The function should parse each field and make sure that the return value is exactly of type *NewDiaryEntry*. This means we should check each field separately.

Once again, we have a type issue: what is the type of the parameter *object*? Since the *object* is the body of a request, Express has typed it as *any*. Since the idea of this function is to map fields of unknown type to fields of the correct type and check whether they are defined as expected, this might be the rare case in which we *want to allow the **any** type*.

However, if we type the object as *any*, ESLint complains about that:

![Screenshot of a VSCode editor showing an ESLint error message popup. The error highlights the use of the 'any' type in TypeScript code, with the ESLint rule @typescript-eslint/no-explicit-any flagging it as an error. The code editor has a dark theme with syntax highlighting, and a Quick Fix suggestion is visible recommending to use 'unknown' instead.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/0eKdzaJeJwmW9HWaxzO8vErtjJXhgU.png)

We could ignore the ESlint rule but a better idea is to follow one of the advices the editor gives in the *Quick Fix* and set the parameter type to *unknown*:

```typescript
import type { NewDiaryEntry } from './types.ts';

const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  const newEntry: NewDiaryEntry = {
    // ...
  }

  return newEntry;
}

export default parseNewDiaryEntry;
```

[unknown](https://www.typescriptlang.org/docs/handbook/2/functions.html#unknown) is the ideal type for our kind of situation of input validation, since we don't yet need to define the type to match *any* type, but can first verify the type and then confirm that is the expected type. With the use of *unknown*, we also don't need to worry about the *@typescript-eslint/no-explicit-any* ESlint rule, since we are not using *any*. However, we might still need to use *any* in some cases in which we are not yet sure about the type and need to access the properties of an object of type *any* to validate or type-check the property values themselves.

> **A sidenote from the editor**
>
> *If you are like me and hate having a code in broken state for a long time due to incomplete typing, you could start by "faking" the function:*
>
> ```typescript
> const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
>
>  console.log(object); // now object is no longer unused
>  const newEntry: NewDiaryEntry = {
>    weather: 'cloudy', // fake the return value
>    visibility: 'great',
>    date: '2026-1-1',
>    comment: 'fake news'
>  };
>
>  return newEntry;
> };
> ```
>
> *So before the real data and types are ready to use, I am just returning here something that has for sure the right type. The code stays in an operational state all the time and my blood pressure remains at normal levels.*

---

### Type guards

Let us start creating the parsers for each of the fields of the parameter *object: unknown*.

To validate the *comment* field, we need to check that it exists and to ensure that it is of the type *string*.

The function should look something like this:

```typescript
const parseComment = (comment: unknown): string => {
  if (!comment || !isString(comment)) {
    throw new Error('Incorrect or missing comment');
  }

  return comment;
};
```

The function gets a parameter of type *unknown* and returns it as the type *string* if it exists and is of the right type.

The string validation function looks like this:

```typescript
const isString = (text: unknown): text is string => {
  return typeof text === 'string' || text instanceof String;
};
```

The function is a so-called [type guard](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#using-type-predicates). That means it is a function that returns a boolean *and* has a *type predicate* as the return type. In our case, the type predicate is:

```typescript
text is string
```

The general form of a type predicate is *parameterName is Type* where the *parameterName* is the name of the function parameter and *Type* is the targeted type.

If the type guard function returns true, the TypeScript compiler knows that the tested variable has the type that was defined in the type predicate.

Before the type guard is called, the actual type of the variable *comment* is not known:

![Screenshot of VSCode showing a type tooltip hovering over a variable named 'comment'. The tooltip displays the type as 'unknown', indicating that before the type guard check, TypeScript has no specific type information about the variable.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/Qdl59vpM6xqHKus3ZkuvsA3WbGKe2f.png)

But after the call, if the code proceeds past the exception (that is, the type guard returned true), then the compiler knows that the *comment* is of type *string*:

![Screenshot of VSCode showing a type tooltip hovering over the 'comment' variable after passing through a type guard. The tooltip now displays the type as 'string', demonstrating how TypeScript's type narrowing works - after the isString() type guard returns true, the compiler knows the variable is a string.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/0FexcUthA7uu0t42UHcpphSPdHVwav.png)

The use of a type guard that returns a type predicate is one way to do [type narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html), that is, to give a variable a more strict or accurate type. As we will soon see there are also other kinds of [type guards](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) available.

> **Side note: testing if something is a string**
>
> *Why do we have two conditions in the string type guard?*
>
> ```typescript
> const isString = (text: unknown): text is string => {
>  return typeof text === 'string' || text instanceof String;
> }
> ```
>
> *Would it not be enough to write the guard like this?*
>
> ```typescript
> const isString = (text: unknown): text is string => {
>  return typeof text === 'string';
> }
> ```
>
> *Most likely, the simpler form is good enough for all practical purposes. However, if we want to be sure, both conditions are needed. There are two different ways to create string in JavaScript, one as a primitive and the other as an object, which both work a bit differently when compared to the **typeof** and **instanceof** operators:*
>
> ```typescript
> const a = "I'm a string primitive";
> const b = new String("I'm a String Object");
> typeof a; --> returns 'string'
> typeof b; --> returns 'object'
> a instanceof String; --> returns false
> b instanceof String; --> returns true
> ```
>
> *However, it is unlikely that anyone would create a string with a constructor function. Most likely the simpler version of the type guard would be just fine.*

Next, let's consider the *date* field. Parsing and validating the date object is pretty similar to what we did with comments. Since TypeScript doesn't know a type for a date, we need to treat it as a *string*. We should however still use JavaScript-level validation to check whether the date format is acceptable.

We will add the following functions:

```typescript
const isDate = (date: string): boolean => {
  return Boolean(Date.parse(date));
};

const parseDate = (date: unknown): string => {
  if (!date || !isString(date) || !isDate(date)) {
      throw new Error('Incorrect or missing date: ' + date);
  }
  return date;
};
```

The code is nothing special. The only thing is that we can't use a type predicate based type guard here since a date in this case is only considered to be a *string*. Note that even though the *parseDate* function accepts the *date* variable as *unknown*, after we check its type with *isString*, TypeScript compiler knows its type is *string*, which is why we can give the variable to the *isDate* function requiring a string without any problems.

Finally, we are ready to move on to the last two types, *Weather* and *Visibility*.

We would like the validation and parsing to work as follows:

```typescript
const parseWeather = (weather: unknown): Weather => {
  if (!weather || !isString(weather) || !isWeather(weather)) {
      throw new Error('Incorrect or missing weather: ' + weather);
  }
  return weather;
};
```

The question is: how can we validate that the string is of a specific form? One possible way to write the type guard would be this:

```typescript
const isWeather = (str: string): str is Weather => {
  return ['sunny', 'rainy', 'cloudy', 'stormy'].includes(str);
};
```

This would work just fine, but the problem is that the list of possible values for Weather does not necessarily stay in sync with the type definitions if the type is altered. This is most certainly not good, since we would like to have just one source for all possible weather types.

---

### as const object

In our case, a better solution would be to improve the actual Weather type. Instead of a type alias, we can use a [const object](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-4.html#const-assertions), which allows us to use the actual values in our code at runtime, not only in the compilation phase.

Let us redefine the type Weather as follows:

```typescript
export const Weather = {
  Sunny: 'sunny',
  Rainy: 'rainy',
  Cloudy: 'cloudy',
  Stormy: 'stormy',
  Windy: 'windy',
} as const;

export type Weather = typeof Weather[keyof typeof Weather];
```

Note that we define both a const object and a type with the same name. TypeScript allows this because they live in separate namespaces. The type is derived directly from the object's values, so the two always stay in sync automatically.

Now we can check that a string is one of the accepted values, and the type guard can be written like this:

```typescript
const isWeather = (param: string): param is Weather => {
  return (Object.values(Weather) as string[]).includes(param);
};
```

The parser has nothing surprising:

```typescript
const parseWeather = (weather: unknown): Weather => {
  if (!weather || !isString(weather) || !isWeather(weather)) {
    throw new Error('Incorrect or missing weather: ' + weather);
  }
  return weather;
};
```

We still need to give the same treatment to Visibility. The *const object* looks as follows:

```typescript
export const Visibility = {
  Great: 'great',
  Good: 'good',
  Ok: 'ok',
  Poor: 'poor',
} as const;

export type Visibility = typeof Visibility[keyof typeof Visibility];
```

The type guard and the parser are below:

```typescript
const isVisibility = (param: string): param is Visibility => {
  return (Object.values(Visibility) as string[]).includes(param);
};

const parseVisibility = (visibility: unknown): Visibility => {
  if (!visibility || !isString(visibility) || !isVisibility(visibility)) {
    throw new Error('Incorrect or missing visibility: ' + visibility);
  }
  return visibility;
};
```

---

*as const* objects are typically used when there is a set of predetermined values that are not expected to change in the future. They offer a great way to validate our incoming values while remaining plain JavaScript objects, which makes them more flexible in some situations than [enums](https://www.typescriptlang.org/docs/handbook/enums.html), which were earlier a popular choice to define a similar purpose.

> **What are actually the type Visibility and the Visibility**
>
> When we defined
>
> ```typescript
> export const Visibility = {
>   Great: 'great',
>   Good: 'good',
>   Ok: 'ok',
>   Poor: 'poor',
> } as const;
>
> export type Visibility = typeof Visibility[keyof typeof Visibility];
> ```
>
> we defined two distinct thing, the *const object Visibility* and *type Visibility*, interestingly TypeScript allows both to coexist despite they have the same name.
>
> If we hover the type Visiblitity, we see what it actually is:
>
> ![Screenshot of VSCode showing a TypeScript type tooltip when hovering over the Visibility type. The tooltip displays the resolved type as '"great" | "good" | "ok" | "poor"', showing that the type is a union of four string literal values derived from the const object using typeof and keyof.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/tEQatIGx3lDxoejUZhUOZ1ZzeVYOeI.png)
>
> So the it just resolves to the union of four literal string values. It can be used e.g. as follows:
>
> ```typescript
> const x: Visibility = "great";
> const y: Visibility = Visibility.Ok;
> ```
>
> In the latter example, we are using the const object Visibility and assigning its value Ok (that is, the string *ok*) to y.
>
> We could also use different names for the const object and the type:
>
> ```typescript
> export const VisibilityValues = {
>   Great: 'great',
>   Good: 'good',
>   Ok: 'ok',
>   Poor: 'poor',
> } as const;
>
> export type Visibility = typeof VisibilityValues[keyof typeof VisibilityValues];
> ```
>
> The the guard would be
>
> ```typescript
> import { VisibilityValues, type Visibility, ... } from './types.ts';
>
> const isVisibility = (param: string): param is Visibility => {
>   return (Object.values(VisibilityValues) as string[]).includes(param);
> };
> ```
>
> In this case, we would also need to separately import both now. As we now understand what is going on, we will stick to using the same name for both since it makes the code a bit less verbose.

There is however one question still remaining. What in earth is

```typescript
typeof Visibility[keyof typeof Visibility]
```

Let us break it down step by step. The *typeof Visibility* gives you the type of the object itself:

```typescript
{
  readonly Great: 'great',
  readonly Good: 'good',
  readonly Ok: 'ok',
  readonly Poor: 'poor',
}
```

The *keyof* extracts all keys of that type as a union:

```typescript
'Great' | 'Good' | 'Ok' | 'Poor'
```

The last layer, index into *typeof Visibility* using those keys, this looks up the *value types* for each key from the object *Visibility*, producing a union of all value types (that in our case are just string literals):

```typescript
'great' | 'good' | 'ok' | 'poor'
```

Finally, we can finalize the parseNewDiaryEntry function that takes care of validating and parsing the fields of the POST body. There is, however, one more thing to take care of. If we try to access the fields of the parameter *object* as follows:

```typescript
const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  const newEntry: NewDiaryEntry = {
    comment: parseComment(object.comment),
    date: parseDate(object.date),
    weather: parseWeather(object.weather),
    visibility: parseVisibility(object.visibility)
  };

  return newEntry;
};
```

The code does not pass the typecheck:

![Screenshot of VSCode editor showing TypeScript type errors with red squiggly underlines. The error message indicates "Object is of type 'unknown'" when trying to access properties like object.comment, object.date, object.weather, and object.visibility on an unknown typed parameter, demonstrating TypeScript's strict type checking that prevents property access on unknown types without type narrowing.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/sYtL4B4tLyDZhRVZSJgLLnPd8JLzAz.png)

This is because the [unknown](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html#new-unknown-top-type) type does not allow any operations, so accessing the fields is not possible:

We can again fix the problem by type narrowing. We now have two type guards, the first checks that the parameter object exists and that it has the type *object*. After this, the second type guard uses the [in](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#the-in-operator-narrowing) operator to ensure that the object has all the desired fields:

```typescript
const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  if ( !object || typeof object !== 'object' ) {
    throw new Error('Incorrect or missing data');
  }

  if ('comment' in object && 'date' in object && 'weather' in object && 'visibility' in object)  {
    const newEntry: NewDiaryEntry = {
      weather: parseWeather(object.weather),
      visibility: parseVisibility(object.visibility),
      date: parseDate(object.date),
      comment: parseComment(object.comment)
    };

    return newEntry;
  }

  throw new Error('Incorrect data: some fields are missing');
};
```

If the guard does not evaluate to true, an exception is thrown.

The use of the operator *in* actually guarantees that the fields indeed exist in the object. Because of that, the existence checks in the parsers are no longer needed:

```typescript
const parseVisibility = (visibility: unknown): Visibility => {
  // check !visibility removed
  if (!isString(visibility) || !isVisibility(visibility)) {
      throw new Error('Incorrect visibility: ' + visibility);
  }
  return visibility;
};
```

If a field, e.g. *comment* would be optional, the type narrowing should take that into account, and the operator [in](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#the-in-operator-narrowing) could not be used quite as we did here, since the *in* test requires the field to be present.

If we now try to create a new diary entry with invalid or missing fields, we are getting an appropriate error message:

![Screenshot of a terminal or API testing tool (like Postman or curl) showing an HTTP POST request to the /api/diaries endpoint with invalid or missing data. The response shows a 400 Bad Request status with an error message indicating which fields are incorrect or missing, demonstrating the request validation working correctly.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/YtHyGuyWbQauGi8FaOun3MzGOakxda.png)

The source code of the application can be found on [GitHub](https://github.com/fullstack-hy2020/flightdiary/tree/part1).

---

## Exercise 13. Patientor backend, step5

> **Tries:** 1 | **Points:** 0/1
>
> Create a POST endpoint */api/patients* for adding patients. Ensure that you can add patients also from the frontend. You can create unique ids of type *string* using the [uuid](https://github.com/uuidjs/uuid) library:
>
> ```typescript
> import { v1 as uuid } from 'uuid'
>
> const id = uuid()
> ```

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

## Exercise 14. Patientor backend, step6

> **Tries:** 1 | **Points:** 0/1
>
> Set up safe parsing, validation and type predicate to the POST */api/patients* request.
>
> Refactor the *gender* field to use a const object based type.

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

#### Using schema validation libraries

Writing a validator to the request body can be a huge burden. Thankfully there exists several *schema validator libraries* that can help. Let us now have a look at [Zod](https://zod.dev/) that works pretty well with TypeScript.

Let us get started:

```bash
npm install zod
```

Parsers of the primitive valued fields such as

```typescript
const isString = (text: unknown): text is string => {
  return typeof text === 'string' || text instanceof String;
};

const parseComment = (comment: unknown): string => {
  if (!isString(comment)) {
    throw new Error('Incorrect comment');
  }

  return comment;
};
```

are easy to replace as follows:

```typescript
import { z } from 'zod';

// ...

const parseComment = (comment: unknown): string => {
  return z.string().parse(comment);
};
```

First the [string](https://zod.dev/?id=strings) method of Zod is used to define the required type (or *schema* in Zod terms). After that the value (which is of the type *unknown*) is parsed with the method [parse](https://zod.dev/?id=parse), which returns the value in the required type or throws an exception.

We do not actually need the helper function *parseComment* anymore and can use the Zod parser directly:

```typescript
export const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  if ( !object || typeof object !== 'object' ) {
    throw new Error('Incorrect or missing data');
  }

  if ('comment' in object && 'date' in object && 'weather' in object && 'visibility' in object)  {
    const newEntry: NewDiaryEntry = {
      weather: parseWeather(object.weather),
      visibility: parseVisibility(object.visibility),
      date: parseDate(object.date),
      comment: z.string().parse(object.comment)
    };

    return newEntry;
  }

  throw new Error('Incorrect data: some fields are missing');
};
```

Zod has a bunch of string specific validations, eg. one that validates if a string is a valid [date](https://zod.dev/?id=dates), so we get also rid of the date field parser:

```typescript
export const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  if ( !object || typeof object !== 'object' ) {
    throw new Error('Incorrect or missing data');
  }

  if ('comment' in object && 'date' in object && 'weather' in object && 'visibility' in object)  {
    const newEntry: NewDiaryEntry = {
      weather: parseWeather(object.weather),
      visibility: parseVisibility(object.visibility),
      date: z.iso.date().parse(object.date),
      comment: z.string().optional().parse(object.comment)
    };

    return newEntry;
  }

  throw new Error('Incorrect data: some fields are missing');
};
```

We have also decided to make the field comment [optional](https://zod.dev/?id=optional).

The Zod validator for [enums](https://zod.dev/api?id=enums) suits to a case where possible inputs are a fixed set of strings, and that is the case with weather and the visibility.

```typescript
export const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  if ( !object || typeof object !== 'object' ) {
    throw new Error('Incorrect or missing data');
  }

  if ('comment' in object && 'date' in object && 'weather' in object && 'visibility' in object)  {
    const newEntry: NewDiaryEntry = {
      weather: z.enum(Weather).parse(object.weather),
      visibility: z.enum(Visibility).parse(object.visibility),
      date: z.iso.date().parse(object.date),
      comment: z.string().parse(object.comment)
    };

    return newEntry;
  }

  throw new Error('Incorrect data: some fields are missing');
};
```

We have so far just used Zod to parse the type or schema of individual fields, but we can go one step further and define the whole *new diary entry* as a Zod [object](https://zod.dev/?id=objects) schema:

```typescript
const NewEntrySchema = z.object({
  weather: z.enum(Weather),
  visibility: z.enum(Visibility),
  date: z.iso.date(),
  comment: z.string().optional()
});
```

Now it is just enough to call *parse* of the defined schema:

```typescript
export const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  return NewEntrySchema.parse(object);
};
```

With the help from [documentation](https://zod.dev/basics?id=handling-errors) we could also improve the error handling:

```typescript
import { z } from 'zod';

//

router.post('/', (req, res) => {
  try {
    const newDiaryEntry = parseNewDiaryEntry(req.body);
    const addedEntry = diaryService.addDiary(newDiaryEntry);
    res.json(addedEntry);
  } catch (error: unknown) {
    if (error instanceof z.ZodError) {
      res.status(400).send({ error: error.issues });
    } else {
      res.status(400).send({ error: 'unknown error' });
    }
  }
});
```

The response in case of error looks pretty good:

![Screenshot of an API response showing a JSON error object returned when Zod validation fails. The response has a 400 status code and contains an 'error' field with an array of validation issues. Each issue describes which field failed validation and why, demonstrating Zod's detailed error reporting for invalid request bodies.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/5dHQErYWn3OaXwZXcBk8GePuyYdxcH.png)

We could develop our solution still some steps further. Our type definitions currently look like this:

```typescript
export interface DiaryEntry {
  id: number;
  date: string;
  weather: Weather;
  visibility: Visibility;
  comment?: string;
}

export type NewDiaryEntry = Omit<DiaryEntry, 'id'>;
```

So besides the type *NewDiaryEntry* we have also the Zod schema *NewEntrySchema* that defines the shape of a new entry. We can use the schema to [infer](https://zod.dev/?id=type-inference) the type:

```typescript
import { z } from 'zod';
import { NewEntrySchema } from './utils.ts'

export interface DiaryEntry {
  id: number;
  date: string;
  weather: Weather;
  visibility: Visibility;
  comment?: string;
}

// infer the type from schema
export type NewDiaryEntry = z.infer<typeof NewEntrySchema>;
```

We could take this even a bit further and define the *DiaryEntry* based on *NewDiaryEntry*:

```typescript
export type NewDiaryEntry = z.infer<typeof NewEntrySchema>;

export interface DiaryEntry extends NewDiaryEntry {
  id: number;
}
```

This removes all the duplication in the type and schema definitions. It feels a bit backward, but unfortunately, the opposite is not possible: we can not define the Zod schema based on TypeScript type definitions, so now the Zod schema is the single source of our type. Since the schema is also the basis of the type, we'll move the schema definition to the file *types.ts*.

The current state of the source code can be found in the part2 branch of [this](https://github.com/fullstack-hy2020/flightdiary/tree/part2) GitHub repository.

---

### Parsing request body in middleware

We can now get rid of this method altogether

```typescript
export const parseNewDiaryEntry = (object: unknown): NewDiaryEntry => {
  return NewEntrySchema.parse(object);
};
```

and just call the Zod-parser directly in the route handler:

```typescript
import { NewEntrySchema, type NonSensitiveDiaryEntry } from '../types.ts';

router.post('/', (req, res) => {
  try {
    const newDiaryEntry = NewEntrySchema.parse(req.body);
    const addedEntry = diaryService.addDiary(newDiaryEntry);
    res.json(addedEntry);
  } catch (error: unknown) {
    if (error instanceof z.ZodError) {
      res.status(400).send({ error: error.issues });
    } else {
      res.status(400).send({ error: 'unknown error' });
    }
  }
});
```

We could go even one step further. Instead of explicitly calling the request body parsing method in the route handler, the input validation could also be performed in a middleware function.

We have also added the type definitions to the route handler parameters, and shall also use types in the middleware function *newDiaryParser*:

```typescript
import express, { type Request, type Response, type NextFunction } from 'express';

// ...

const newDiaryParser = (req: Request, _res: Response, next: NextFunction) => {
  try {
    NewEntrySchema.parse(req.body);
    next();
  } catch (error: unknown) {
    next(error);
  }
};
```

The middleware just calls the schema parser on the request body. If the parsing throws an exception, it is passed to the error handling middleware.

So after the request passes this middleware, it *is known that the request body is a proper new diary entry*. We can tell this fact to TypeScript compiler by giving a type parameter to the *Request* type:

```typescript
router.post('/', newDiaryParser, (req: Request<unknown, unknown, NewDiaryEntry>, res: Response<DiaryEntry>) => {
  const addedEntry = diaryService.addDiary(req.body);
  res.json(addedEntry);
});
```

Thanks to the middleware, the request body is now known to be of right type and it can be directly given as parameter to the function *diaryService.addDiary*.

The syntax of the *Request<unknown, unknown, NewDiaryEntry>* looks a bit odd. The *Request* is a [generic type](https://www.typescriptlang.org/docs/handbook/2/generics.html#generic-types) with several type parameters. The third type parameter represents the request body, and in order to give it the value *NewDiaryEntry* we have to give *some* value to the two first parameters. We decide to define those *unknown* since we do not need those for now.

Since the possible errors in validation are now handled in the error handling middleware, we need to define one that handles the Zod errors properly:

```typescript
const errorMiddleware = (error: unknown, _req: Request, res: Response, next: NextFunction) => {
  if (error instanceof z.ZodError) {
    res.status(400).send({ error: error.issues });
  } else {
    next(error);
  }
};

router.post('/', newDiaryParser, (req: Request<unknown, unknown, NewDiaryEntry>, res: Response<DiaryEntry>) => {
  // ...
});

router.use(errorMiddleware);
```

The final version of the source code can be found in the part3 branch of [this](https://github.com/fullstack-hy2020/flight-diary/tree/part3) GitHub repository.

---

## Exercise 15. Patientor backend, step7

> **Tries:** 1 | **Points:** 0/1
>
> Use Zod to validate the requests to the POST endpoint */api/patients*.

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

## Exercise 16. Checkup

> **Tries:** 1 | **Points:** 0/1
>
> Similarly to [Exercise 8](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#7d395c4f-af73-40ae-a915-01b600ff8f93), run the tests in the directory *patientor-api-tests*. Tests assume that the backend runs on port 3001.
>
> Enable those also in GitHub by modifying *.github/workflows/patientor-api-tests.yml* as follows:
>
> ```yaml
> name: Patientor API Tests
> on:
>   push:
>     branches: [ main, master ]
> ```

> **Complete and lock the previous chapter to unlock exercises in this chapter.**

---

### Mark Chapter as Complete

> **Complete and lock the previous chapter to unlock exercises in this chapter.**
