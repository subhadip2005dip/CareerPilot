import { NextRequest, NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL;

export async function POST(request: NextRequest) {
  try {
    const { role, questions, answers } = await request.json();

    if (!PYTHON_API_URL) {
      return NextResponse.json(
        { error: 'Python API URL not configured' },
        { status: 500 }
      );
    }

    const response = await fetch(`${PYTHON_API_URL}/interview/feedback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        role,
        questions,
        answers,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || data.error || `API error: ${response.statusText}`);
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Interview evaluation error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to evaluate answer' },
      { status: 500 }
    );
  }
}
