# Open Deep Research 🔬

A powerful AI-powered research assistant that automates scientific literature reviews using Claude AI, Exa Search, and Firecrawl.

## Features

- **Automated Literature Review**: Conducts iterative searches to build comprehensive research reports
- **Intelligent Search Strategy**: Claude AI autonomously decides what to search for based on findings
- **Full Article Analysis**: Retrieves and analyzes complete articles, not just abstracts
- **Customizable Research**: Configure number of iterations, AI model, and search parameters
- **Live Progress Tracking**: Real-time updates on research progress
- **Export Options**: Download reports in Markdown and research data in JSON

## Setup on Replit

### 1. Fork the Repl

1. Go to [Replit](https://replit.com)
2. Create a new Python Repl
3. Upload the project files

### 2. Configure Secrets

In your Replit project, go to the "Secrets" tab and add:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
EXA_API_KEY=your_exa_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

### 3. Install Dependencies

The dependencies will be automatically installed from `requirements.txt` when you run the app.

### 4. Run the Application

Click the "Run" button in Replit. The Streamlit app will start and provide you with a URL to access the application.

## How to Use

1. **Enter Your Research Query**: Type in a scientific topic you want to research
2. **Configure Settings**:
   - Number of iterations (3-15)
   - Claude model selection
   - Results per search
   - Advanced options (content length, date filtering)
3. **Start Research**: Click the "Start Research" button
4. **Monitor Progress**: Watch live updates as the AI conducts research
5. **Review Results**: Read the comprehensive report and download it

## API Keys

To use this application, you need API keys from:

- **Anthropic** (Claude AI): [Get API Key](https://console.anthropic.com/)
- **Exa**: [Get API Key](https://exa.ai/)
- **Firecrawl**: [Get API Key](https://www.firecrawl.dev/)

## Example Queries

- Effects of metformin on liver health
- Latest advances in CRISPR gene editing for cancer treatment
- Impact of microplastics on marine ecosystems
- Neuroplasticity in adult brain recovery after stroke
- Role of gut microbiome in autoimmune diseases

## Technical Stack

- **Frontend**: Streamlit
- **AI Model**: Claude (Anthropic)
- **Search API**: Exa
- **Content Scraping**: Firecrawl
- **Hosting**: Replit

## Security Notes

- API keys are stored securely in Replit Secrets
- No user data is stored permanently
- All research is conducted in real-time

## Troubleshooting

### API Keys Not Working
- Ensure all three API keys are correctly added to Replit Secrets
- Check that the keys have the necessary permissions

### Research Takes Too Long
- Reduce the number of iterations
- Use a faster Claude model (Sonnet instead of Opus)

### Error Messages
- Check the console logs for detailed error information
- Ensure you have sufficient API credits for all services

## Contributing

Feel free to fork this project and submit pull requests for improvements!

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check the [Issues](https://github.com/yourusername/ai-research-assistant/issues) page
- Contact support at your-email@example.com

---

Built with ❤️ using Streamlit and Claude AI