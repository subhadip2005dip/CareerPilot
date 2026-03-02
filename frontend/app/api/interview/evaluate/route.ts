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

    // Read response body once
    let text = '';
    try {
      text = await response.text();
    } catch (e) {
      console.error('Failed to read response:', e);
      throw new Error('Failed to read backend response');
    }

    // Check if response is ok
    if (!response.ok) {
      console.error('Backend error response:', { status: response.status, text: text.slice(0, 500) });
      let errorMsg = `Backend returned ${response.status}`;
      try {
        const errorJson = JSON.parse(text);
        errorMsg = errorJson.detail || errorJson.error || errorMsg;
      } catch {
        errorMsg = text.slice(0, 200) || errorMsg;
      }
      throw new Error(errorMsg);
    }

    // Parse JSON
    if (!text) {
      throw new Error('Empty response body from backend');
    }

    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      console.error('JSON parse error:', e);
      throw new Error('Backend returned invalid JSON');
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
