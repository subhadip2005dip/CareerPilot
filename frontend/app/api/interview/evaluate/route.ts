import { NextRequest, NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL;

export async function POST(request: NextRequest) {
  try {
    const { question, answer, sessionId, difficulty } = await request.json();

    if (!PYTHON_API_URL) {
      return NextResponse.json(
        { error: 'Python API URL not configured' },
        { status: 500 }
      );
    }

    const response = await fetch(`${PYTHON_API_URL}/evaluate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        answer,
        sessionId,
        difficulty,
      }),
    });

    if (!response.ok) {
      throw new Error(`Interview API error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Interview evaluation error:', error);
    return NextResponse.json(
      { error: 'Failed to evaluate answer' },
      { status: 500 }
    );
  }
}
