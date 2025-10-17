# Atlas Project Decisions

## Licensing

- **License**: MIT License
- **Rationale**: Chosen to ensure the project remains open source and allows for maximum flexibility in use, while aligning with the user's philosophy of self-ownership and open access.

## Usage Intent

- **Purpose**: The project is intended for personal use only, specifically for the creator's individual knowledge management and cognitive amplification.
- **Commercial Use**: Explicitly stated that there is no commercial intent or expectation. While the MIT license legally permits commercial use, the project's spirit and design are geared towards a single-user, non-commercial application.
- **Community Use**: While primarily for personal use, the open-source nature allows others to use it for their own single-person, non-commercial purposes if they choose.

## Technology Choices (High-Level)

- **Python/FastAPI**: Chosen for its efficiency, modern features, and suitability for building robust APIs, likely leveraging existing Python expertise.
- **OpenRouter for LLM Access**: Decision to use OpenRouter for LLM access via API, providing flexibility and potentially cost-effectiveness compared to direct API access from individual LLM providers.
- **Raspberry Pi as Primary Deployment**: Decision to target Raspberry Pi for deployment reflects a commitment to self-hosting, low-cost operation, and personal control over the infrastructure.
- **Mac Mini M4 for Intensive Tasks**: A pragmatic decision to utilize more powerful hardware for computationally intensive tasks like transcription, acknowledging the limitations of the Raspberry Pi for certain workloads.
- **Spinning Disks for Storage**: A deliberate choice for large-scale data storage, indicating a focus on accumulating vast amounts of personal data.