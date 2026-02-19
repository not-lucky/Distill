# Deploying app to internet

Next, let's connect the frontend we made in [part 2](/en/part2) to our own backend.

In the previous part, the frontend could ask for the list of notes from the json-server we had as a backend, from the address [http://localhost:3001/notes](http://localhost:3001/notes). Our backend has a slightly different URL structure now, as the notes can be found at [http://localhost:3001/api/notes](http://localhost:3001/api/notes). Let's change the attribute **baseUrl** in the frontend notes app at *src/services/notes.js* like so:

```js
import axios from 'axios'
const baseUrl = 'http://localhost:3001/api/notes'
const getAll = () => {
  const request = axios.get(baseUrl)
  return request.then(response => response.data)
}

// ...

export default { getAll, create, update }
```

Now frontend's GET request to [http://localhost:3001/api/notes](http://localhost:3001/api/notes) does not work for some reason:

![Get request showing error in dev tools](/static/da88e17cb078c89a6e7ba30d61fab0e6/5a190/3ae.png)
*Detailed Description: A screenshot of browser developer tools showing a failed network request. A red 'X' is visible next to a GET request to http://localhost:3001/api/notes, indicating a failed attempt to fetch data.*

What's going on here? We can access the backend from a browser and from postman without any problems.

### Same origin policy and CORS

The issue lies with a thing called *same origin policy*. A URL's origin is defined by the combination of protocol (AKA scheme), hostname, and port.

```text
http://example.com:80/index.html
  
protocol: http
host: example.com
port: 80
```

When you visit a website (e.g. [http://example.com](http://example.com)), the browser issues a request to the server on which the website (example.com) is hosted. The response sent by the server is an HTML file that may contain one or more references to external assets/resources hosted either on the same server that *example.com* is hosted on or a different website. When the browser sees reference(s) to a URL in the source HTML, it issues a request. If the request is issued using the URL that the source HTML was fetched from, then the browser processes the response without any issues. However, if the resource is fetched using a URL that doesn't share the same origin(scheme, host, port) as the source HTML, the browser will have to check the *Access-Control-Allow-origin* response header. If it contains *\** on the URL of the source HTML, the browser will process the response, otherwise the browser will refuse to process it and throws an error.

The **same-origin policy** is a security mechanism implemented by browsers in order to prevent session hijacking among other security vulnerabilities.

In order to enable legitimate cross-origin requests (requests to URLs that don't share the same origin) W3C came up with a mechanism called **CORS**(Cross-Origin Resource Sharing). According to [Wikipedia](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing):

> *Cross-origin resource sharing (CORS) is a mechanism that allows restricted resources (e.g. fonts) on a web page to be requested from another domain outside the domain from which the first resource was served. A web page may freely embed cross-origin images, stylesheets, scripts, iframes, and videos. Certain "cross-domain" requests, notably Ajax requests, are forbidden by default by the same-origin security policy.*

The problem is that, by default, the JavaScript code of an application that runs in a browser can only communicate with a server in the same [origin](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy). Because our server is in localhost port 3001, while our frontend is in localhost port 5173, they do not have the same origin.

Keep in mind, that [same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy) and CORS are not specific to React or Node. They are universal principles regarding the safe operation of web applications.

We can allow requests from other *origins* by using Node's [cors](https://github.com/expressjs/cors) middleware.

In your backend repository, install *cors* with the command

```bash
npm install cors
```

take the middleware to use and allow for requests from all origins:

```js
const cors = require('cors')

app.use(cors())
```

**Note:** When you are enabling cors, you should think about how you want to configure it. In the case of our application, since the backend is not expected to be visible to the public in the production environment, it may make more sense to only enable cors from a specific origin (e.g. the front end).

Now most of the features in the frontend work! The functionality for changing the importance of notes has not yet been implemented on the backend so naturally that does not yet work in the frontend. We shall fix that later.

You can read more about CORS from [Mozilla's page](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS).

The setup of our app now looks as follows:

![diagram of react app and browser](/static/20b558375e438a856a0520e775f93239/37523/100_25.png)
*Detailed Description: A technical diagram illustrating the architecture of the application. It shows a 'Browser' containing a 'React App' which makes a request to a 'Node/Express Server' running on 'localhost:3001'. The server then returns a response to the browser.*

The react app running in the browser now fetches the data from node/express-server that runs in localhost:3001.

### Application to the Internet

Now that the whole stack is ready, let's move our application to Internet.

There is an ever-growing number of services that can be used to host an app on the internet. The developer-friendly services like PaaS (i.e. Platform as a Service) take care of installing the execution environment (eg. Node.js) and could also provide various services such as databases.

For a decade, [Heroku](http://heroku.com) was dominating the PaaS scene. Unfortunately the free tier Heroku ended at 27th November 2022. This is very unfortunate for many developers, especially students. Heroku is still very much a viable option if you are willing to spend some money. They also have [a student program](https://www.heroku.com/students) that provides some free credits.

We are now introducing two services [Fly.io](https://fly.io/) and [Render](https://render.com/). Fly.io offers more flexibility as a service, but it has also recently become paid. Render offers some free compute time, so if you want to complete the course without costs, choose Render. Setting up Render might also be easier in some cases, as Render does not require any installations on your own machine.

There are also some other free hosting options that work well for this course, at least for all parts other than part 11 (CI/CD) which might have one tricky exercise for other platforms.

Some course participants have also used the following services:

* [Replit](https://replit.com)
* [CodeSandBox](https://codesandbox.io)

If you know easy-to-use and free services for hosting NodeJS, please let us know!

For both Fly.io and Render, we need to change the definition of the port our application uses at the bottom of the *index.js* file in the backend like so:

```js
const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})
```

Now we are using the port defined in the [environment variable](https://en.wikipedia.org/wiki/Environment_variable) *PORT* or port 3001 if the environment variable *PORT* is undefined. It is possible to configure the application port based on the environment variable both in Fly.io and in Render.

#### Fly.io

*Note that you may need to give your credit card number to Fly.io!*

If you decide to use [Fly.io](https://fly.io/) begin by installing their flyctl executable following [this guide](https://fly.io/docs/hands-on/install-flyctl/). After that, you should [create a Fly.io account](https://fly.io/docs/hands-on/sign-up/).

Start by [authenticating](https://fly.io/docs/hands-on/sign-in/) via the command line with the command

```bash
fly auth login
```

Note if the command *fly* does not work on your machine, you can try the longer version *flyctl*. Eg. on MacOS, both forms of the command work.

*If you do not get the flyctl to work in your machine, you could try Render (see next section), it does not require anything to be installed in your machine.*

Initializing an app happens by running the following command in the root directory of the app

```bash
fly launch --no-deploy
```

Give the app a name or let Fly.io auto-generate one. Pick a region where the app will be run. Do not create a Postgres database for the app and do not create an Upstash Redis database, since these are not needed.

Fly.io creates a file *fly.toml* in the root of your app where we can configure it. To get the app up and running we *might* need to do a small addition to the configuration:

```bash
[build]

[env]
  PORT = "3001" # add this

[http_service]
  internal_port = 3001 # ensure that this is same as PORT
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
  processes = ["app"]
```

We have now defined in the part [env] that environment variable PORT will get the correct port (defined in part [http_service]) where the app should create the server.

We are now ready to deploy the app to the Fly.io servers. That is done with the following command:

```bash
fly deploy
```

If all goes well, the app should now be up and running. You can open it in the browser with the command

```bash
fly apps open
```

A particularly important command is *fly logs*. This command can be used to view server logs. It is best to keep logs always visible!

**Note:** Fly may create 2 machines for your app, if it does then the state of the data in your app will be inconsistent between requests, i.e. you would have two machines each with its own notes variable, you could POST to one machine then your next GET could go to another machine. You can check the number of machines by using the command "$ fly scale show", if the COUNT is greater than 1 then you can enforce it to be 1 with the command "$ fly scale count 1". The machine count can also be checked on the dashboard.

**Note:** In some cases (the cause is so far unknown) running Fly.io commands especially on Windows WSL (Windows Subsystem for Linux) has caused problems. If the following command just hangs

```bash
flyctl ping -o personal
```

your computer can not for some reason connect to Fly.io. If this happens to you, [this](https://github.com/fullstack-hy2020/misc/blob/master/fly_io_problem.md) describes one possible way to proceed.

If the output of the below command looks like this:

```bash
$ flyctl ping -o personal
35 bytes from fdaa:0:8a3d::3 (gateway), seq=0 time=65.1ms
35 bytes from fdaa:0:8a3d::3 (gateway), seq=1 time=28.5ms
35 bytes from fdaa:0:8a3d::3 (gateway), seq=2 time=29.3ms
...
```

then there are no connection problems!

Whenever you make changes to the application, you can take the new version to production with a command

```bash
fly deploy
```

#### Render

*Note that you may need to give your credit card number to Render!*

The following assumes that the [sign in](https://dashboard.render.com/) has been made with a GitHub account.

After signing in, let us create a new "web service":

![Image showing the option to create a new Web Service](/static/918351e5ad479c327ac578c0743a0811/5a190/r1.png)
*Detailed Description: A screenshot of the Render dashboard showing a 'New' button with a dropdown menu. The 'Web Service' option is highlighted, indicating the path to create a new hosting instance for a web application.*

The app repository is then connected to Render:

![Image showing the application repository on Render.](/static/75040aae9bcb08b7aa53fd201ed900a9/5a190/r2.png)
*Detailed Description: A screenshot showing the interface where a GitHub repository is linked to Render. It lists a repository named 'fullstack-notes-backend' with a 'Connect' button next to it.*

The connection seems to require that the app repository is public.

Next we will define the basic configurations. If the app is *not* at the root of the repository the *Root directory* needs to be given a proper value:

![image showing the Root Directory field as optional](/static/8411e07f2b7ee2665f61341b7253e49f/5a190/r3.png)
*Detailed Description: A screenshot of the configuration settings on Render. It highlights the 'Root Directory' field, which is noted as optional, and shows other fields like 'Name', 'Region', and 'Branch'.*

After this, the app starts up in the Render. The dashboard tells us the app state and the url where the app is running:

![The top left corner of the image shows the status of the application and its URL](/static/4a478e6ef9229324ff606f2ada7b0b46/5a190/r4.png)
*Detailed Description: A screenshot of the Render service dashboard. It shows the status 'Live' in green, the application name 'notes-backend', and the public URL provided by Render (e.g., https://notes-backend.onrender.com).*

According to the [documentation](https://render.com/docs/deploys) every commit to GitHub should redeploy the app. For some reason this is not always working.

Fortunately, it is also possible to manually redeploy the app:

![Menu with the option to deploy latest commit highlighted](/static/b87d1b6ab7339294ad1f00453155e733/5a190/r5.png)
*Detailed Description: A screenshot showing the 'Manual Deploy' dropdown menu on Render. The 'Deploy latest commit' option is visible, allowing the user to trigger a deployment manually.*

Also, the app logs can be seen in the dashboard:

![Image with the logs tab highlighted on the left corner. On the right side, the application logs](/static/798d2488fb450327abf2b6729faaaeec/5a190/r7.png)
*Detailed Description: A screenshot of the 'Logs' tab in the Render dashboard. The right pane shows the real-time output from the application, including a message 'Server running on port 10000'.*

We notice now from the logs that the app has been started in the port 10000. The app code gets the right port through the environment variable PORT so it is essential that the file *index.js* has been updated in the backend as follows:

```js
const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
})
```

### Frontend production build

So far we have been running React code in *development mode*. In development mode the application is configured to give clear error messages, immediately render code changes to the browser, and so on.

When the application is deployed, we must create a [production build](https://vitejs.dev/guide/build.html) or a version of the application that is optimized for production.

A production build for applications created with Vite can be created with the command [npm run build](https://vitejs.dev/guide/build.html).

Let's run this command from the *root of the notes frontend project* that we developed in [Part 2](/en/part2).

This creates a directory called *dist* which contains the only HTML file of our application (*index.html*) and the directory *assets*. [Minified](https://en.wikipedia.org/wiki/Minification_(programming)) version of our application's JavaScript code will be generated in the *dist* directory. Even though the application code is in multiple files, all of the JavaScript will be minified into one file. All of the code from all of the application's dependencies will also be minified into this single file.

The minified code is not very readable. The beginning of the code looks like this:

```js
!function(e){function r(r){for(var n,f,i=r[0],l=r[1],a=r[2],c=0,s=[];c<i.length;c++)f=i[c],o[f]&&s.push(o[f][0]),o[f]=0;for(n in l)Object.prototype.hasOwnProperty.call(l,n)&&(e[n]=l[n]);for(p&&p(r);s.length;)s.shift()();return u.push.apply(u,a||[]),t()}function t(){for(var e,r=0;r<u.length;r++){for(var t=u[r],n=!0,i=1;i<t.length;i++){var l=t[i];0!==o[l]&&(n=!1)}n&&(u.splice(r--,1),e=f(f.s=t[0]))}return e}var n={},o={2:0},u=[];function f(r){if(n[r])return n[r].exports;var t=n[r]={i:r,l:!1,exports:{}};return e[r].call(t.exports,t,t.exports,f),t.l=!0,t.exports}f.m=e,f.c=n,f.d=function(e,r,t){f.o(e,r)||Object.defineProperty(e,r,{enumerable:!0,get:t})},f.r=function(e){"undefined"!==typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"})}
```

### Serving static files from the backend

One option for deploying the frontend is to copy the production build (the *dist* directory) to the root of the backend directory and configure the backend to show the frontend's *main page* (the file *dist/index.html*) as its main page.

We begin by copying the production build of the frontend to the root of the backend. With a Mac or Linux computer, the copying can be done from the frontend directory with the command

```bash
cp -r dist ../backend
```

If you are using a Windows computer, you may use either [copy](https://www.windows-commandline.com/windows-copy-command-syntax-examples/) or [xcopy](https://www.windows-commandline.com/xcopy-command-syntax-examples/) command instead. Otherwise, simply copy and paste.

The backend directory should now look as follows:

![bash screenshot of ls showing dist directory](/static/6148bf347bb9674c782d5dfc9bdd643b/5a190/27v.png)
*Detailed Description: A terminal window showing the output of an 'ls' command. The directory contents include 'dist', 'index.js', 'node_modules', 'package.json', and 'package-lock.json', showing that the frontend build has been successfully copied into the backend project.*

To make Express show *static content*, the page *index.html* and the JavaScript, etc., it fetches, we need a built-in middleware from Express called [static](http://expressjs.com/en/starter/static-files.html).

When we add the following amidst the declarations of middlewares

```js
app.use(express.static('dist'))
```

whenever Express gets an HTTP GET request it will first check if the *dist* directory contains a file corresponding to the request's address. If a correct file is found, Express will return it.

Now HTTP GET requests to the address *www.serversaddress.com/index.html* or *www.serversaddress.com* will show the React frontend. GET requests to the address *www.serversaddress.com/api/notes* will be handled by the backend code.

Because of our situation, both the frontend and the backend are at the same address, we can declare *baseUrl* as a [relative](https://www.w3.org/TR/WD-html40-970917/htmlweb.html#h-5.1.2) URL. This means we can leave out the part declaring the server.

```js
import axios from 'axios'
const baseUrl = '/api/notes'
const getAll = () => {
  const request = axios.get(baseUrl)
  return request.then(response => response.data)
}

// ...
```

After the change, we have to create a new production build of the frontend and copy it to the root of the backend directory.

The application can now be used from the *backend* address [http://localhost:3001](http://localhost:3001):

![Notes application in localhost:3001](/static/00b60846d754ead099038271e2e54ecc/5a190/28new.png)
*Detailed Description: A screenshot of the application running in a browser at http://localhost:3001. It shows the 'Notes' header, a list of notes with 'make important' buttons, and a form to add a new note, demonstrating the frontend is being served by the backend.*

Our application now works exactly like the [single-page app](/en/part0/fundamentals_of_web_apps#single-page-app) example application we studied in part 0.

When we use a browser to go to the address [http://localhost:3001](http://localhost:3001), the server returns the *index.html* file from the *dist* directory. The contents of the file are as follows:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React</title>
    <script type="module" crossorigin src="/assets/index-5f6faa37.js"></script>
    <link rel="stylesheet" href="/assets/index-198af077.css">
  </head>
  <body>
    <div id="root"></div>
    
  </body>
</html>
```

The file contains instructions to fetch a CSS stylesheet defining the styles of the application, and one *script* tag that instructs the browser to fetch the JavaScript code of the application - the actual React application.

The React code fetches notes from the server address [http://localhost:3001/api/notes](http://localhost:3001/api/notes) and renders them to the screen. The communication between the server and the browser can be seen in the *Network* tab of the developer console:

![Network tab of notes application on backend](/static/7e90543c1d9697b1058225a877364cb9/5a190/29new.png)
*Detailed Description: A screenshot of the browser's Network developer tools. It shows a list of requests, including the main page '/', 'index-5f6faa37.js', 'index-198af077.css', and a JSON fetch from 'notes', showing the complete loading sequence of the single-page application.*

The setup that is ready for a product deployment looks as follows:

![diagram of deployment ready react app](/static/ee40b09299b5cbf969989a2ad320d198/db910/101.png)
*Detailed Description: An architectural diagram showing the 'Deployment' state. It depicts a 'Browser' interacting with a single 'Node/Express Server' on 'localhost:3001'. The server hosts both the 'Static Files' (dist directory) and the 'API' (/api/notes).*

Unlike when running the app in a development environment, everything is now in the same node/express-backend that runs in localhost:3001. When the browser goes to the page, the file *index.html* is rendered. That causes the browser to fetch the production version of the React app. Once it starts to run, it fetches the json-data from the address localhost:3001/api/notes.

### The whole app to the internet

After ensuring that the production version of the application works locally, we are ready to move the whole application to the selected host service.

**In the case of Fly.io** the new deployment is done with the command

```bash
fly deploy
```

**NOTE:** The *.dockerignore* file in your project directory lists files not uploaded during deployment. The dist directory may be included by default. If that's the case, remove its reference from the .dockerignore file, ensuring your app is properly deployed.

**In the case of Render**, commit the changes, and push the code to GitHub again. Make sure the directory *dist* is not ignored by git on the backend. A push to GitHub *might* be enough. If the automatic deployment does not work, select the "manual deploy" from the Render dashboard.

The application works perfectly, except we haven't added the functionality for changing the importance of a note to the backend yet.

![screenshot of notes application](/static/7003b3eacf4ce56213d8be4bea2df167/5a190/30new.png)
*Detailed Description: A screenshot of the 'Notes' application successfully deployed and running on a live web URL. The interface shows several notes, demonstrating that the full-stack application is functional on the internet.*

*Detailed Description: changing the importance DOES NOT work yet since the backend has no implementation for it yet.*

Our application saves the notes to a variable. If the application crashes or is restarted, all of the data will disappear.

The application needs a database. Before we introduce one, let's go through a few things.

The setup now looks like as follows:

![diagram of react app on fly.io](/static/cb4cbf3b34d7096b0de655cc6e114e18/5a190/102.png)
*Detailed Description: An architectural diagram showing the application in 'Production'. It shows a 'Browser' connected via the 'Internet' to a 'Server' (Fly.io or Render). The server hosts the 'Node/Express App' which includes the 'Static Files' and the 'API'.*

The node/express-backend now resides in the Fly.io/Render server. When the root address is accessed, the browser loads and executes the React app that fetches the json-data from the Fly.io/Render server.

### Streamlining deploying of the frontend

To create a new production build of the frontend without extra manual work, let's add some npm-scripts to the *package.json* of the backend repository.

#### Fly.io script

The scripts look like this:

```json
{
  "scripts": {
    // ...
    "build:ui": "rm -rf dist && cd ../notes-frontend/ && npm run build && cp -r dist ../notes-backend",
    "deploy": "fly deploy",
    "deploy:full": "npm run build:ui && npm run deploy",    
    "logs:prod": "fly logs"
  }
}
```

The script *npm run build:ui* builds the frontend and copies the production version under the backend repository. The script *npm run deploy* releases the current backend to Fly.io.

*npm run deploy:full* combines these two scripts, i.e., *npm run build:ui* and *npm run deploy*.

There is also a script *npm run logs:prod* to show the Fly.io logs.

Note that the directory paths in the script *build:ui* depend on the location of the frontend and backend directories in the file system.

##### Note for Windows users

Note that the standard shell commands in `build:ui` do not natively work in Windows. Powershell in Windows works differently, in which case the script could be written as

```json
"build:ui": "@powershell Remove-Item -Recurse -Force dist && cd ../frontend && npm run build && @powershell Copy-Item dist -Recurse ../backend",
```

If the script does not work on Windows, confirm that you are using Powershell and not Command Prompt. If you have installed Git Bash or another Linux-like terminal, you may be able to run Linux-like commands on Windows as well.

#### Render

Note: When you attempt to deploy your backend to Render, make sure you have a separate repository for the backend and deploy that github repo through Render, attempting to deploy through your Fullstackopen repository will often throw "ERR path ....package.json".

In case of Render, the scripts look like the following

```json
{
  "scripts": {
    //...
    "build:ui": "rm -rf dist && cd ../frontend && npm run build && cp -r dist ../backend",
    "deploy:full": "npm run build:ui && git add . && git commit -m uibuild && git push"
  }
}
```

The script *npm run build:ui* builds the frontend and copies the production version under the backend repository. *npm run deploy:full* contains also the necessary *git* commands to update the backend repository.

Note that the directory paths in the script *build:ui* depend on the location of the frontend and backend directories in the file system.

> **NB** On Windows, npm scripts are executed in cmd.exe as the default shell which does not support bash commands. For the above bash commands to work, you can change the default shell to Bash (in the default Git for Windows installation) as follows:

```md
npm config set script-shell "C:\\Program Files\\git\\bin\\bash.exe"
```

Another option is the use of [shx](https://www.npmjs.com/package/shx).

### Proxy

Changes on the frontend have caused it to no longer work in development mode (when started with command *npm run dev*), as the connection to the backend does not work.

![Network dev tools showing a 404 on getting notes](/static/c2dc22eab2be6e45278c02055c079123/5a190/32new.png)
*Detailed Description: A screenshot of the Network tab in browser developer tools showing a 404 Not Found error for a request to /api/notes. This illustrates the failure that occurs when the frontend (on port 5173) tries to access the relative path without a proxy.*

This is due to changing the backend address to a relative URL:

```js
const baseUrl = '/api/notes'
```

Because in development mode the frontend is at the address *localhost:5173*, the requests to the backend go to the wrong address *localhost:5173/api/notes*. The backend is at *localhost:3001*.

If the project was created with Vite, this problem is easy to solve. It is enough to add the following declaration to the *vite.config.js* file of the frontend directory.

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
      },
    }
  },}
)
```

After restarting, the React development environment will act as [proxy](https://vitejs.dev/config/server-options.html#server-proxy). If the React code makes an HTTP request to a path starting with *http://localhost:5173/api*, the request will be forwarded to the server at *http://localhost:3001*. Requests to other paths will be handled normally by the development server.

Now the frontend is also working correctly. It functions both in development mode and in production mode together with the server. Since from the frontend's perspective all requests are made to http://localhost:5173, which is the single origin, there is no longer a need for the backend's cors middleware. Therefore, we can remove references to the cors library from the backend's *index.js* file and remove *cors* from the project's dependencies:

```bash
npm remove cors
```

We have now successfully deployed the entire application to the internet. There are many other ways to implement deployments. For example, deploying the frontend code as its own application may be sensible in some situations, as it can facilitate the implementation of an automated [deployment pipeline](https://martinfowler.com/bliki/DeploymentPipeline.html). A deployment pipeline refers to an automated and controlled way to move code from the developer's machine through various tests and quality control stages to the production environment. This topic is covered in [part 11](/en/part11) of the course.

The current backend code can be found on [Github](https://github.com/fullstack-hy2020/part3-notes-backend/tree/part3-3), in the branch *part3-3*. The changes in frontend code are in *part3-1* branch of the [frontend repository](https://github.com/fullstack-hy2020/part2-notes-frontend/tree/part3-1).

### Exercises 3.9.-3.11

The following exercises don't require many lines of code. They can however be challenging, because you must understand exactly what is happening and where, and the configurations must be just right.

#### 3.9 Phonebook backend step 9

Make the backend work with the phonebook frontend from the exercises of the previous part. Do not implement the functionality for making changes to the phone numbers yet, that will be implemented in exercise 3.17.

You will probably have to do some small changes to the frontend, at least to the URLs for the backend. Remember to keep the developer console open in your browser. If some HTTP requests fail, you should check from the *Network*-tab what is going on. Keep an eye on the backend's console as well. If you did not do the previous exercise, it is worth it to print the request data or *request.body* to the console in the event handler responsible for POST requests.

#### 3.10 Phonebook backend step 10

Deploy the backend to the internet, for example to Fly.io or Render. If you are using Fly.io the commands should be run in the root directory of the backend (that is, in the same directory where the backend package.json is).

**PRO TIP:** When you deploy your application to Internet, it is worth it to at least in the beginning keep an eye on the logs of the application **AT ALL TIMES**.

Test the deployed backend with a browser and Postman or VS Code REST client to ensure it works.

Create a README.md at the root of your repository, and add a link to your online application to it.

#### 3.11 Full Stack Phonebook

Generate a production build of your frontend, and add it to the Internet application using the method introduced in this part.

Also, make sure that the frontend still works locally (in development mode when started with command *npm run dev*).

If you use Render, make sure the directory *dist* is not ignored by git on the backend.

**NOTE:** You shall NOT be deploying the frontend directly at any stage of this part. Only the backend repository is deployed throughout the whole part. The frontend production build is added to the backend repository, and the backend serves it as described in the section [Serving static files from the backend](/en/part3/deploying_app_to_internet#serving-static-files-from-the-backend).
