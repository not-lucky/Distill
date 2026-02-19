# Validation and ESLint

There are usually constraints that we want to apply to the data that is stored in our application's database. Our application shouldn't accept notes that have a missing or empty *content* property. The validity of the note is checked in the route handler:

```js
app.post('/api/notes', (request, response) => {
  const body = request.body
  if (!body.content) {
    return response.status(400).json({ error: 'content missing' })
  }
  // ...
})
```

If the note does not have the *content* property, we respond to the request with the status code *400 bad request*.

One smarter way of validating the format of the data before it is stored in the database is to use the [validation](https://mongoosejs.com/docs/validation.html) functionality available in Mongoose.

We can define specific validation rules for each field in the schema:

```js
const noteSchema = new mongoose.Schema({
  content: {
    type: String,
    minLength: 5,
    required: true
  },
  important: Boolean
})
```

The *content* field is now required to be at least five characters long and it is set as required, meaning that it can not be missing. We have not added any constraints to the *important* field, so its definition in the schema has not changed.

The *minLength* and *required* validators are [built-in](https://mongoosejs.com/docs/validation.html#built-in-validators) and provided by Mongoose. The Mongoose [custom validator](https://mongoosejs.com/docs/validation.html#custom-validators) functionality allows us to create new validators if none of the built-in ones cover our needs.

If we try to store an object in the database that breaks one of the constraints, the operation will throw an exception. Let's change our handler for creating a new note so that it passes any potential exceptions to the error handler middleware:

```js
app.post('/api/notes', (request, response, next) => {
  const body = request.body

  const note = new Note({
    content: body.content,
    important: body.important || false,
  })

  note.save()
    .then(savedNote => {
      response.json(savedNote)
    })
    .catch(error => next(error))
})
```

Let's expand the error handler to deal with these validation errors:

```js
const errorHandler = (error, request, response, next) => {
  console.error(error.message)

  if (error.name === 'CastError') {
    return response.status(400).send({ error: 'malformatted id' })
  } else if (error.name === 'ValidationError') {
    return response.status(400).json({ error: error.message })
  }

  next(error)
}
```

When validating an object fails, we return the following default error message from Mongoose:

![postman showing error message. The image shows a Postman interface where a POST request to http://localhost:3001/api/notes has failed. The response body displays a JSON error message: "error": "Note validation failed: content: Path `content` (`ed`) is shorter than the minimum allowed length (5).". The status code is 400 Bad Request.](/static/6beb35ed56d2e06e0eda3e36dea9f426/5a190/50.png)

### Deploying the database backend to production

The application should work almost as-is in Fly.io/Render. We do not have to generate a new production build of the frontend since changes thus far were only on our backend.

The environment variables defined in dotenv will only be used when the backend is not in *production mode*, i.e. Fly.io or Render.

For production, we have to set the database URL in the service that is hosting our app.

In Fly.io that is done *fly secrets set*:

```bash
fly secrets set MONGODB_URI='mongodb+srv://fullstack:thepasswordishere@cluster0.a5qfl.mongodb.net/noteApp?retryWrites=true&w=majority'
```

When the app is being developed, it is more than likely that something fails. Eg. when I deployed my app for the first time with the database, not a single note was seen:

![browser showing no notes appearing. A screenshot of a browser window displaying a web application titled "Notes". The page header shows "Notes" and buttons for "all", "important", and "nonimportant". Below the header, it says "Noteapp, Department of Computer Science, University of Helsinki 2024". No notes are visible in the list area.](/static/ba06b14a502f7da32b06c9cd2e79f97b/5a190/fly-problem1.png)

The network tab of the browser console revealed that fetching the notes did not succeed, the request just remained for a long time in the *pending* state until it failed with status code 502.

The browser console has to be open *all the time!*

It is also vital to follow continuously the server logs. The problem became obvious when the logs were opened with *fly logs*:

![fly.io server log showing connecting to undefined. A terminal window showing Fly.io logs. A specific line is highlighted where the application logs "connecting to undefined". This indicates that the MONGODB_URI environment variable is not set.](/static/92ac2c6e2e4d0f84bb7a5a5317708d75/5a190/fly-problem3.png)

The database url was *undefined*, so the command *fly secrets set MONGODB_URI* was forgotten.

You will also need to whitelist the fly.io app's IP address in MongoDB Atlas. If you don't MongoDB will refuse the connection.

Sadly, fly.io does not provide you a dedicated IPv4 address for your app, so you will need to allow all IP addresses in MongoDB Atlas.

When using Render, the database url is given by defining the proper env in the dashboard:

![render dashboard showing the MONGODB_URI env variable. A screenshot of the Render dashboard's Environment tab. It shows an environment variable named MONGODB_URI with its corresponding value (partially obscured) being set for the application.](/static/ae7c73092becbbef8aa45299e9b8fbcd/5a190/render-env.png)

The Render Dashboard shows the server logs:

![render dashboard with arrow pointing to server running on port 10000. A screenshot of the Render dashboard's Logs tab. A red arrow points to a log entry stating "Server running on port 10000", confirming the backend has started successfully.](/static/798d2488fb450327abf2b6729faaaeec/5a190/r7.png)

You can find the code for our current application in its entirety in the *part3-6* branch of [this GitHub repository](https://github.com/fullstack-hy2020/part3-notes-backend/tree/part3-6).

### Exercises 3.19.-3.21.

#### 3.19*: Phonebook database, step 7

Expand the validation so that the name stored in the database has to be at least three characters long.

Expand the frontend so that it displays some form of error message when a validation error occurs. Error handling can be implemented by adding a *catch* block as shown below:

```js
personService
    .create({ ... })
    .then(createdPerson => {
      // ...
    })
    .catch(error => {
      // this is the way to access the error message
      console.log(error.response.data.error)
    })
```

You can display the default error message returned by Mongoose, even though they are not as readable as they could be:

![phonebook screenshot showing person validation failure. A screenshot of a "Phonebook" web application. A red error message box at the top displays: "Person validation failed: name: Path `name` (`Li`) is shorter than the minimum allowed length (3).". Below, the form shows "name: Li" and "number: 040-123456".](/static/fddf847e340f060549c3029f464a5493/5a190/56e.png)

**NB:** On update operations, mongoose validators are off by default. [Read the documentation](https://mongoosejs.com/docs/validation.html) to determine how to enable them.

#### 3.20*: Phonebook database, step 8

Add validation to your phonebook application, which will make sure that phone numbers are of the correct form. A phone number must:

- have length of 8 or more
- be formed of two parts that are separated by -, the first part has two or three numbers and the second part also consists of numbers
    - eg. 09-1234556 and 040-22334455 are valid phone numbers
    - eg. 1234556, 1-22334455 and 10-22-334455 are invalid

Use a [Custom validator](https://mongoosejs.com/docs/validation.html#custom-validators) to implement the second part of the validation.

If an HTTP POST request tries to add a person with an invalid phone number, the server should respond with an appropriate status code and error message.

#### 3.21 Deploying the database backend to production

Generate a new "full stack" version of the application by creating a new production build of the frontend, and copying it to the backend directory. Verify that everything works locally by using the entire application from the address [http://localhost:3001/](http://localhost:3001/).

Push the latest version to Fly.io/Render and verify that everything works there as well.

**NOTE:** You shall NOT be deploying the frontend directly at any stage of this part. Only the backend repository is deployed throughout the whole part. The frontend production build is added to the backend repository, and the backend serves it as described in the section [Serving static files from the backend](/en/part3/deploying_app_to_internet#serving-static-files-from-the-backend).

### Lint

Before we move on to the next part, we will take a look at an important tool called [lint](https://en.wikipedia.org/wiki/Lint_(software)). Wikipedia says the following about lint:

> *Generically, lint or a linter is any tool that detects and flags errors in programming languages, including stylistic errors. The term lint-like behavior is sometimes applied to the process of flagging suspicious language usage. Lint-like tools generally perform static analysis of source code.*

In compiled statically typed languages like Java, IDEs like NetBeans can point out errors in the code, even ones that are more than just compile errors. Additional tools for performing [static analysis](https://en.wikipedia.org/wiki/Static_program_analysis) like [checkstyle](https://checkstyle.sourceforge.io), can be used for expanding the capabilities of the IDE to also point out problems related to style, like indentation.

In the JavaScript universe, the current leading tool for static analysis (aka "linting") is [ESlint](https://eslint.org/).

Let's add ESLint as a *development dependency* for the backend. Development dependencies are tools that are only needed during the development of the application. For example, tools related to testing are such dependencies. When the application is run in production mode, development dependencies are not needed.

Install ESLint as a development dependency for the backend with the command:

```bash
npm install eslint @eslint/js --save-dev
```

The contents of the package.json file will change as follows:

```js
{
  //...
  "dependencies": {
    "dotenv": "^16.4.7",
    "express": "^5.1.0",
    "mongoose": "^8.11.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.22.0",
    "eslint": "^9.22.0"
  }
}
```

The command added a *devDependencies* section to the file and included the packages *eslint* and *@eslint/js*, and installed the required libraries into the *node_modules* directory.

After this we can initialize a default ESlint configuration with the command:

```bash
npx eslint --init
```

We will answer all of the questions:

![terminal output from ESlint init. A terminal screenshot showing the interactive process of 'npx eslint --init'. It shows questions about how ESLint should be used, what type of modules the project uses, which framework (None), if the project uses TypeScript (No), where the code runs (Node), and the desired format for the config file (JavaScript).](/static/0232394f437e1b8d60891bd7b7b1dcbe/5a190/lint1.png)

The configuration will be saved in the generated *eslint.config.mjs* file.

### Formatting the Configuration File

Let's reformat the configuration file *eslint.config.mjs* from its current form to the following:

```js
import globals from 'globals'

export default [
  {
    files: ['**/*.js'],
    languageOptions: {
      sourceType: 'commonjs',
      globals: { ...globals.node },
      ecmaVersion: 'latest',
    },
  },
]
```

So far, our ESLint configuration file defines the *files* option with *["**/*.js"]*, which tells ESLint to look at all JavaScript files in our project folder. The *languageOptions* property specifies options related to language features that ESLint should expect, in which we defined the *sourceType* option as "commonjs". This indicates that the JavaScript code in our project uses the CommonJS module system, allowing ESLint to parse the code accordingly.

The *globals* property specifies global variables that are predefined. The spread operator applied here tells ESLint to include all global variables defined in the *globals.node* settings such as the *process*. In the case of browser code we would define here *globals.browser* to allow browser specific global variables like *window*, and *document*.

Finally, the *ecmaVersion* property is set to "latest". This sets the ECMAScript version to the latest available version, meaning ESLint will understand and properly lint the latest JavaScript syntax and features.

We want to make use of [ESLint's recommended](https://eslint.org/docs/latest/use/configure/configuration-files#using-predefined-configurations) settings along with our own. The *@eslint/js* package we installed earlier provides us with predefined configurations for ESLint. We'll import it and enable it in the configuration file:

```js
import globals from 'globals'
import js from '@eslint/js'
// ...

export default [
  js.configs.recommended,
  {
    // ...
  },
]
```

We've added the *js.configs.recommended* to the top of the configuration array, this ensures that ESLint's recommended settings are applied first before our own custom options.

Let's continue building the configuration file. Install a [plugin](https://eslint.style/packages/js) that defines a set of code style-related rules:

```bash
npm install --save-dev @stylistic/eslint-plugin
```

Import and enable the plugin, and add these four code style rules:

```js
import globals from 'globals'
import js from '@eslint/js'
import stylisticJs from '@stylistic/eslint-plugin'
export default [
  {
    // ...
    plugins: { 
      '@stylistic/js': stylisticJs,
    },
    rules: { 
      '@stylistic/js/indent': ['error', 2],
      '@stylistic/js/linebreak-style': ['error', 'unix'],
      '@stylistic/js/quotes': ['error', 'single'],
      '@stylistic/js/semi': ['error', 'never'],
    }, 
  },
]
```

The [plugins](https://eslint.org/docs/latest/use/configure/plugins) property provides a way to extend ESLint's functionality by adding custom rules, configurations, and other capabilities that are not available in the core ESLint library. We've installed and enabled the *@stylistic/eslint-plugin*, which adds JavaScript stylistic rules for ESLint. In addition, rules for indentation, line breaks, quotes, and semicolons have been added. These four rules are all defined in the [Eslint styles plugin](https://eslint.style/packages/js).

**Note for Windows users:** The linebreak style is set to *unix* in the style rules. It is recommended to use Unix-style linebreaks (*\n*) regardless of your operating system, as they are compatible with most modern operating systems and facilitate collaboration when multiple people are working on the same files. If you are using Windows-style linebreaks, ESLint will produce the following errors: *Expected linebreaks to be 'LF' but found 'CRLF'*. In this case, configure Visual Studio Code to use Unix-style linebreaks by following [this guide](https://stackoverflow.com/questions/48692741/how-can-i-make-all-line-endings-eols-in-all-files-in-visual-studio-code-unix).

### Running the Linter

Inspecting and validating a file like *index.js* can be done with the following command:

```bash
npx eslint index.js
```

It is recommended to create a separate *npm script* for linting:

```json
{
  // ...
  "scripts": {
    "start": "node index.js",
    "dev": "node --watch index.js",
    "test": "echo \"Error: no test specified\" && exit 1",
    "lint": "eslint ."
    // ...
  },
  // ...
}
```

Now the *npm run lint* command will check every file in the project.

Files in the *dist* directory also get checked when the command is run. We do not want this to happen, and we can accomplish this by adding an object with the [ignores](https://eslint.org/docs/latest/use/configure/ignore) property that specifies an array of directories and files we want to ignore.

```js
// ...
export default [
  js.configs.recommended,
  {
    files: ['**/*.js'],
    // ...
  },
  { 
    ignores: ['dist/**'], 
  },
]
```

This causes the entire *dist* directory to not be checked by ESlint.

Lint has quite a lot to say about our code:

![terminal output of ESlint errors. A terminal screenshot showing the output of 'npm run lint'. It lists multiple errors in 'index.js', such as 'trailing spaces not allowed', 'expected indentation of 2 spaces but found 4', and 'extra semicolon'.](/static/cdf7d27db507f48c4ab9f7bd59f8071f/5a190/53ea.png)

A better alternative to executing the linter from the command line is to configure an *eslint-plugin* to the editor, that runs the linter continuously. By using the plugin you will see errors in your code immediately. You can find more information about the Visual Studio ESLint plugin [here](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint).

The VS Code ESlint plugin will underline style violations with a red line:

![Screenshot of vscode ESlint plugin showing errors. A screenshot of a code editor (VS Code) showing 'index.js'. Several lines of code are underlined in red, indicating ESLint violations. Hovering over one reveals the error: "'request' is defined but never used. (no-unused-vars)".](/static/64cf2fbae36000083aa1e48292aed8f2/5a190/54a.png)

This makes errors easy to spot and fix right away.

### Adding More Style Rules

ESlint has a vast array of [rules](https://eslint.org/docs/rules/) that are easy to take into use by editing the *eslint.config.mjs* file.

Let's add the [eqeqeq](https://eslint.org/docs/rules/eqeqeq) rule that warns us if equality is checked with anything but the triple equals operator. The rule is added under the rules field in the configuration file.

```js
export default [
  // ...
  rules: {
    // ...
   eqeqeq: 'error',
  },
  // ...
]
```

While we're at it, let's make a few other changes to the rules.

Let's prevent unnecessary [trailing spaces](https://eslint.style/rules/no-trailing-spaces) at the ends of lines, require that [there is always a space before and after curly braces](https://eslint.style/rules/object-curly-spacing), and also demand a consistent use of whitespaces in the function parameters of arrow functions.

```js
export default [
  // ...
  rules: {
    // ...
    eqeqeq: 'error',
    'no-trailing-spaces': 'error',
    'object-curly-spacing': ['error', 'always'],
    'arrow-spacing': ['error', { before: true, after: true }],
  },
]
```

Our default configuration takes a bunch of predefined rules into use from:

```js
// ...

export default [
  js.configs.recommended,
  // ...
]
```

This includes a rule that warns about *console.log* commands which we don't want to use. Disabling a rule can be accomplished by defining its "value" as 0 or *off* in the configuration file. Let's do this for the *no-console* rule in the meantime.

```js
[
  {
    // ...
    rules: {
      // ...
      eqeqeq: 'error',
      'no-trailing-spaces': 'error',
      'object-curly-spacing': ['error', 'always'],
      'arrow-spacing': ['error', { before: true, after: true }],
      'no-console': 'off',
    },
  },
]
```

Disabling the no-console rule will allow us to use console.log statements without ESLint flagging them as issues. This can be particularly useful during development when you need to debug your code. Here's the complete configuration file with all the changes we have made so far:

```js
import globals from 'globals'
import js from '@eslint/js'
import stylisticJs from '@stylistic/eslint-plugin'

export default [
  js.configs.recommended,
  {
    files: ['**/*.js'],
    languageOptions: {
      sourceType: 'commonjs',
      globals: { ...globals.node },
      ecmaVersion: 'latest',
    },
    plugins: {
      '@stylistic/js': stylisticJs,
    },
    rules: {
      '@stylistic/js/indent': ['error', 2],
      '@stylistic/js/linebreak-style': ['error', 'unix'],
      '@stylistic/js/quotes': ['error', 'single'],
      '@stylistic/js/semi': ['error', 'never'],
      eqeqeq: 'error',
      'no-trailing-spaces': 'error',
      'object-curly-spacing': ['error', 'always'],
      'arrow-spacing': ['error', { before: true, after: true }],
      'no-console': 'off',
    },
  },
  {
    ignores: ['dist/**'],
  },
]
```

**NB** when you make changes to the *eslint.config.mjs* file, it is recommended to run the linter from the command line. This will verify that the configuration file is correctly formatted:

![terminal output from npm run lint. A terminal screenshot showing the successful output of 'npm run lint' after fixing the configuration. It shows no errors or warnings, indicating the project code now adheres to the defined ESLint rules.](/static/07f46b5e48a00a479880e6625fcf342f/5a190/lint2.png)

If there is something wrong in your configuration file, the lint plugin can behave quite erratically.

Many companies define coding standards that are enforced throughout the organization through the ESlint configuration file. It is not recommended to keep reinventing the wheel over and over again, and it can be a good idea to adopt a ready-made configuration from someone else's project into yours. Recently many projects have adopted the Airbnb [Javascript style guide](https://github.com/airbnb/javascript) by taking Airbnb's [ESlint](https://github.com/airbnb/javascript/tree/master/packages/eslint-config-airbnb) configuration into use.

You can find the code for our current application in its entirety in the *part3-7* branch of [this GitHub repository](https://github.com/fullstack-hy2020/part3-notes-backend/tree/part3-7).

### Exercise 3.22.

#### 3.22: Lint configuration

Add ESlint to your application and fix all the warnings.

This was the last exercise of this part of the course. It's time to push your code to GitHub and mark all of your finished exercises to the [exercise submission system](https://studies.cs.helsinki.fi/stats/courses/fullstackopen).
