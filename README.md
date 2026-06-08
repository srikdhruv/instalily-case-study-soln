# PartSelect Chat Agent Case Study

This project implements a simple PartSelect chat agent for refrigerator and dishwasher support. The frontend is the provided React chat template. The backend is a FastAPI service with deterministic flow control, direct OpenAI API integration, and real PartSelect linkouts/scraping tools.

See [docs/architecture.md](docs/architecture.md) for the flow and system design.

## Frontend

```bash
npm start
```

The React app runs at [http://localhost:3000](http://localhost:3000).

The frontend sends the full conversation history to the backend on every chat turn.

## Backend

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create a local `.env` file for server-side keys:

```bash
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_SEARCH_MODEL=gpt-4o-mini-search-preview
```

`.env` is ignored by git. See `.env.example` for the expected keys.

Run the FastAPI backend:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

The backend also works without `OPENAI_API_KEY` by returning deterministic fallback responses, which is useful for local testing.

If your local Python does not have FastAPI/Uvicorn installed yet, you can run the dependency-free development server with the same `/chat` contract:

```bash
python3 -m backend.dev_server
```

## Tests

Core backend logic uses standard-library tests:

```bash
python3 -m unittest backend.tests.test_agent
```

Frontend production build:

```bash
npm run build
```

## Supported V1 Flows

- Troubleshooting for refrigerator and dishwasher symptoms.
- Product/model information lookup.
- Installation help and official PartSelect source links.
- Compatibility checks with conservative `cannot_verify` fallback.
- Part search/purchase linkout.
- Official self-service/order status linkout: https://www.partselect.com/user/self-service/
- Official Instant Repairman linkout: https://www.partselect.com/Instant-Repairman/
- Product URL resolution through a small seeded map plus OpenAI web search, with verification before using product pages.

## Case Study Docs

- [Evaluator plan](docs/evaluator-plan.md)
- [Design decisions and future expansion](docs/design-decisions.md)
- [Architecture](docs/architecture.md)

## Create React App Reference

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
