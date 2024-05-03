const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());
app.use(express.static('public'));

const votes = {
  Alice: 0,
  Bob: 0,
  Charlie: 0,
};

// Endpoint to handle voting
app.post('/vote', (req, res) => {
  const { person } = req.body;
  if (votes[person] !== undefined) {
    votes[person]++;
    res.status(200).json({ success: true });
  } else {
    res.status(400).json({ error: 'Invalid person' });
  }
});

// Endpoint to get the results
app.get('/results', (req, res) => {
  res.json(votes);
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
