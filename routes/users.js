var express = require('express');
var router = express.Router();
const axios = require('axios');

router.get('/', function(req, res, next) {
  res.render("user/testpage")
  return
});

router.post('/checkout', async function (req, res, next) {
  try {

      // Forward the request body to the FastAPI server
      const response = await axios.post("http://127.0.0.1:8000/get_name_quantity_order", req.body);

      console.log("✅ Response from FastAPI:", response.data);

      res.json(response.data);
  } catch (error) {
      console.error("❌ Error forwarding to FastAPI:", error.response ? error.response.data : error.message);
      res.status(500).json({ message: "Error processing order", error: error.message });
  }
});

module.exports = router;

