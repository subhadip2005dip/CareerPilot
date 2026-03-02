import { NextRequest, NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL;

export async function POST(request: NextRequest) {
  try {
    const { message, sessionId, conversationHistory } = await request.json();

    if (!PYTHON_API_URL) {
      return NextResponse.json(
        { error: 'Python API URL not configured' },
        { status: 500 }
      );
    }

    const response = await fetch(`${PYTHON_API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        sessionId,
        conversationHistory,
      }),
    });

    if (!response.ok) {
      throw new Error(`Interview API error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Interview chat error:', error);
    return NextResponse.json(
      { error: 'Failed to get response from interview chatbot' },
      { status: 500 }
    );
  }
}
